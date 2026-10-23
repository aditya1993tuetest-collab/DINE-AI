# Deploying NextLeap DineAI

This guide deploys the existing repository to Render. Nothing here purchases a plan or deploys automatically. Complete the legal/data and account steps before making the site public.

## 1. Prerequisites

- Git and a GitHub repository containing this project.
- Python 3.12-3.14 and Node.js 24 with npm 11 (Node 22+ is supported by the project).
- A Render account and a Groq account.
- Render CLI 2.7.0 or later, authenticated to the target workspace, for the optional workspace-aware Blueprint validation command.
- At least 2 GB free local memory for safer source preprocessing; the downloader streams the 574 MB source, but canonical records are retained during validation.
- Permission to use the Zomato-derived dataset publicly. The visible Hugging Face repository does not currently declare a license.

Do not commit `.env`. Do not put `LLM_API_KEY`, `DATABASE_URL`, or `REDIS_URL` in a `VITE_*` variable.

## 2. Verify the repository before publishing

From `C:\Users\Aditya Agarwal\Desktop\NextLeap` in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e "apps/api[dev]"

python -m ruff check apps/api
python -m ruff format --check apps/api
python -m mypy apps/api/src apps/api/tests
python -m pytest apps/api/tests

Push-Location apps/web
npm ci
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
npx playwright install chromium
npm run test:e2e
Pop-Location
```

Optional container checks, if Docker Desktop is running:

```powershell
docker build -f apps/api/Dockerfile -t nextleap-api:local .
docker build -f apps/web/Dockerfile -t nextleap-web:local .
docker compose config
```

Review what will be committed:

```powershell
git status --short
git diff -- . ':(exclude).env'
git check-ignore .env
```

Validate the Blueprint against the target Render workspace before creating resources:

```powershell
render login
render blueprints validate render.yaml --workspace <render-workspace-id>
```

This workspace-aware check supplements local YAML/schema validation and detects conflicts with resources that already exist in the selected workspace. It does not create or deploy resources.

This repository currently has no initial commit in the audited workspace. Create and review that commit yourself, then push it to a private or public GitHub repository as appropriate. Codex did not push anything.

## 3. Create the Groq credential

In the Groq console, create a server-side API key. Record it in a password manager. Confirm `openai/gpt-oss-120b` is enabled and inspect the account's Limits page; public base limits are not a guarantee for every organization.

Never paste the key into source, GitHub issues, browser variables, or frontend settings.

## 4. Create Render resources from GitHub

1. Sign in to Render and connect the GitHub repository.
2. Choose **New > Blueprint** and select the repository/branch containing `render.yaml`.
3. Render will propose:
   - `nextleap-web` static site
   - `nextleap-api` Docker web service
   - `nextleap-postgres` PostgreSQL database
   - `nextleap-cache` Key Value service
4. Supply the prompted secret:

| Prompt | Value |
|---|---|
| API `LLM_API_KEY` | The Groq secret |

The Blueprint derives all default Render URLs instead of asking you to copy them:

- Web `VITE_API_BASE_URL` references the API service's `RENDER_EXTERNAL_URL`.
- API `WEB_ORIGIN` references the static site's `RENDER_EXTERNAL_URL`.
- API `TRUSTED_HOSTS` references its own `RENDER_EXTERNAL_HOSTNAME`.

These references continue to work if Render adds a suffix because a service name is unavailable. After Blueprint creation, verify the resolved values in each service's Environment page before relying on the frontend. If you add a custom frontend domain, manually override `WEB_ORIGIN` with that exact HTTPS origin (or a comma-separated list that also retains the Render origin) and redeploy the API. Do not use `*`.

5. Approve the Blueprint. The API start script applies Alembic migrations because this free plan has one instance. The platform health check uses `/health/live`.
6. Confirm `https://<api-host>/health/live` returns HTTP 200. `/health/ready` should return HTTP 503 until an active dataset exists; this is expected.

Render free services do not provide shell/one-off jobs, and free pre-deploy commands are unavailable. The next step therefore runs from your trusted local machine against the database external URL.

## 5. Load the pinned dataset

Add the Render PostgreSQL **external** URL as the GitHub Actions repository secret
`RENDER_DATABASE_URL`. The manual-only `.github/workflows/ingest-zomato.yml` workflow uses Python
3.12, forces PostgreSQL TLS through `PGSSLMODE=require`, and never prints the URL.

Run **Ingest pinned Zomato dataset** from the Actions tab with `operation: validate` first. This
downloads the immutable source to runner-local temporary storage, verifies its SHA-256, runs the
existing `--dry-run` pipeline, reports accepted/rejected/duplicate counts and quality gates, and
performs a read-only database-capacity check. It does not publish records.

Review that run's summary. Only after the quality report and capacity projection pass, explicitly
run the workflow again with `operation: publish`. The publish run repeats validation before using
the existing idempotent, transactional publisher. It then confirms the sole active PostgreSQL
version, live readiness, non-empty location/cuisine responses, and the deployed frontend CORS
origin. The workflow is never triggered by a push or pull request.

The capacity guard assumes the 1,000,000,000-byte free-database limit, budgets a conservative
12,288 bytes per accepted canonical restaurant (including related cuisines and indexes), and
retains 100,000,000 bytes of headroom. An identical existing dataset version adds no projected
storage because publication is idempotent.

For emergency operator use outside GitHub Actions, open `nextleap-postgres > Info`, copy the
**external** database URL, treat it as a secret, and run:

```powershell
$env:DATABASE_URL = '<paste-render-external-database-url>'

Push-Location apps/api
python -m alembic upgrade head
Pop-Location

nextleap-data ingest `
  --dataset ManikaSaini/zomato-restaurant-recommendation `
  --revision 5738e9eda2fad49ad51c6e0ed26e761d9b947133 `
  --filename zomato.csv `
  --expected-sha256 4b0c91c37585310d509873dc399fdf739c7d222fcf7a693e4461b23d25a9d43d `
  --dry-run

# Publish only after reviewing the dry-run result and database capacity.
nextleap-data ingest `
  --dataset ManikaSaini/zomato-restaurant-recommendation `
  --revision 5738e9eda2fad49ad51c6e0ed26e761d9b947133 `
  --filename zomato.csv `
  --expected-sha256 4b0c91c37585310d509873dc399fdf739c7d222fcf7a693e4461b23d25a9d43d

nextleap-data list
Remove-Item Env:DATABASE_URL
```

The publication must end with status `active`. Exit code 2 means a quality gate failed; do not
bypass the gate. The source is downloaded only for explicit operator actions, not by API requests,
builds, deploys, or restarts.

Check Render's database storage graph after ingestion. The free database is limited to 1 GB. If the canonical dataset and indexes do not fit, stop and select a larger database—do not weaken validation or store data on the API's ephemeral filesystem.

## 6. Verify the live application

Set local variables to the actual URLs:

```powershell
$apiUrl = 'https://nextleap-api.onrender.com'
$webUrl = 'https://nextleap-web.onrender.com'

Invoke-RestMethod "$apiUrl/health/live"
Invoke-RestMethod "$apiUrl/health/ready"
Invoke-RestMethod "$apiUrl/api/v1/metadata/locations?limit=5"
Invoke-RestMethod "$apiUrl/api/v1/metadata/cuisines?limit=5"
```

Readiness must return HTTP 200 with `status: ready`, `database: available`, `redis: available`, and `activeDataset: true`.

Open `$webUrl` and test:

1. Select a location and leave cuisine optional.
2. Exercise Low, Medium, and High budgets.
3. Exercise minimum ratings, including a query likely to return no matches.
4. Submit a normal query and confirm no more than five results.
5. Compare returned names, ratings, prices, and cuisines with records from the active dataset.
6. Check desktop and mobile widths, keyboard navigation, loading, error, and empty states.
7. In browser developer tools, verify requests go to the Render API over HTTPS and no API key appears in sources, requests, or storage.

The first request after 15 idle minutes can take about one minute while the free API wakes. Warm it by opening `/health/live` shortly before a scheduled demonstration.

## 7. GitHub deployment flow

`render.yaml` uses `autoDeployTrigger: checksPass`. Configure GitHub branch protection so these jobs are required on `main`: `api`, `web`, `repository`, and `security`.

Normal release flow:

```powershell
git switch -c release/deployment-readiness
git add .
git status --short
git commit -m "Prepare restaurant recommender for deployment"
git push -u origin release/deployment-readiness
```

Open a pull request, wait for CI, review the deployment diff, then merge. Render builds the checked commit after the checks pass. The commands above are instructions only; no commit or push was performed during this audit.

## 8. Environment reference

Required API values in Render:

```text
APP_ENV=production
APP_HOST=0.0.0.0
WEB_CONCURRENCY=1
RUN_MIGRATIONS=true
DATABASE_URL=<injected by Render database>
REDIS_URL=<injected by Render Key Value>
REDIS_REQUIRED=true
WEB_ORIGIN=<referenced from nextleap-web RENDER_EXTERNAL_URL>
TRUSTED_HOSTS=<self-referenced RENDER_EXTERNAL_HOSTNAME>
TRUST_PROXY_HEADERS=true
DATABASE_POOL_SIZE=3
DATABASE_MAX_OVERFLOW=2
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
LLM_API_KEY=<Groq secret>
LLM_REASONING_EFFORT=low
MAX_LLM_CANDIDATES=12
MAX_LLM_OUTPUT_TOKENS=700
```

Required frontend build value:

```text
VITE_API_BASE_URL=<referenced from nextleap-api RENDER_EXTERNAL_URL>
VITE_API_TIMEOUT_MS=20000
```

The complete non-secret template is `.env.example`. Render supplies `PORT`; do not hardcode it.

## 9. Troubleshooting

| Symptom | Check |
|---|---|
| API fails during settings load | `LLM_API_KEY`, `REDIS_REQUIRED=true`, and valid `APP_ENV`; do not use quotes copied from a shell |
| `ModuleNotFoundError: psycopg2` | Deploy current code; it converts managed `postgresql://` URLs to `postgresql+psycopg://` |
| `/health/live` fails | Container logs, Render `PORT`, image build, start script permissions |
| `/health/ready` is 503, database unavailable | Database URL, database state, migration logs, region connectivity |
| `/health/ready` is 503, active dataset false | Run the pinned ingestion and inspect `nextleap-data list` |
| `/health/ready` is 503, Redis unavailable | Key Value status and injected `REDIS_URL` |
| Browser shows CORS failure | `WEB_ORIGIN` must exactly match the frontend scheme/hostname; redeploy API after changing it |
| Browser calls localhost or wrong API | Set `VITE_API_BASE_URL` on the static site and redeploy because Vite variables are build-time values |
| Requests time out only after idle | Expected free-service cold start; retry after wake-up or use paid compute |
| Recommendations use fallback mode | Check Groq key/model/limits/provider logs; fallback is an intentional safe behavior |
| Ingestion hash mismatch | Stop. Confirm the exact revision/file; do not remove SHA verification |
| Database exceeds 1 GB or expires | Upgrade/replace the free database and re-ingest or restore; API local disk is not durable |

## 10. Roll back safely

For code/UI regression, open the Render service's **Deploys** page and select **Rollback** on a known-good deployment. Free services retain only the two most recent previous deploys. Alternatively, revert the Git commit and let checks pass before deployment.

For a dataset regression:

```powershell
$env:DATABASE_URL = '<render-external-database-url>'
nextleap-data list
nextleap-data inspect <prior-version-uuid>
nextleap-data activate <prior-version-uuid>
Remove-Item Env:DATABASE_URL
```

Then verify `/health/ready`, metadata, and representative recommendations. Dataset activation is atomic and retained version IDs naturally invalidate old cache keys.

Do not run destructive Alembic downgrades against production data without a verified backup and explicit approval. Free Render PostgreSQL has no backups; use a paid database with backups/PITR for durable production.
