# NextLeap Restaurant Recommendation System

An AI-assisted restaurant recommendation project that combines deterministic filtering with grounded LLM ranking. Restaurant facts remain controlled by the application; an LLM may rank and explain only restaurants supplied by the backend.

For the audited Render deployment path, environment reference, validation evidence, and manual release steps, see [DEPLOYMENT.md](DEPLOYMENT.md), [docs/deployment-audit.md](docs/deployment-audit.md), [docs/deployment-plan.md](docs/deployment-plan.md), and [docs/deployment-validation.md](docs/deployment-validation.md).

The repository implements the Phase 0 foundation and Phase 1 versioned data pipeline from [implementation-plan.md](implementation-plan.md).

## Repository layout

```text
apps/api/                 FastAPI service and Python tests
apps/web/                 React and TypeScript web application
apps/api/alembic/         Phase 1 PostgreSQL migrations
docs/data-profile.md      Source-dataset discovery report
docs/decisions/           Architecture decision records
docs/fixtures/            Small deterministic data fixture
.github/workflows/ci.yml  Continuous integration
compose.yaml              Local API, web, PostgreSQL, and Redis stack
```

Phase 1 migrations live under `apps/api/alembic`; `database/migrations` remains a compatibility placeholder.

## Prerequisites

- Python 3.12 through 3.14
- Node.js 22 or later
- npm 10 or later
- Docker with Compose for the complete local stack (optional for Phase 0 checks)

This machine currently has Python 3.14 and Node.js 24. Docker was not available during Phase 0 verification, so the container files were created but could not be executed locally.

## API setup

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e "apps/api[dev]"
python -m uvicorn restaurant_recommender.main:app --app-dir apps/api/src --reload
```

Open <http://localhost:8000/health/live> or <http://localhost:8000/docs>.

Run backend checks:

```powershell
python -m ruff check apps/api
python -m mypy apps/api/src
python -m pytest apps/api/tests
```

Apply database migrations and exercise the offline fixture pipeline:

```powershell
Set-Location apps/api
python -m alembic upgrade head
Set-Location ../..
nextleap-data ingest --fixture docs/fixtures/restaurants_phase0.csv --dry-run
```

See [docs/phase1-operations.md](docs/phase1-operations.md) for pinned-source ingestion, quality
gates, version inspection, failure recovery, retention, and rollback.

See [docs/phase2-api.md](docs/phase2-api.md) for deterministic recommendation requests, metadata,
no-match relaxations, errors, and request IDs.

See [docs/phase3-operations.md](docs/phase3-operations.md) for grounded LLM configuration, prompt
rollback, failure behavior, audit retention, and evaluation gates.

## Web setup

```powershell
Set-Location apps/web
npm install
npm run dev
```

Open <http://localhost:5173>. Run web checks with:

```powershell
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
```

## Complete local stack

Copy `.env.example` to `.env`, then run:

```powershell
docker compose up --build
```

Services:

- Web: <http://localhost:5173>
- API: <http://localhost:8000>
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

The API does not use PostgreSQL or Redis until later phases; they are included to establish the intended local topology.

## Dataset

The project targets `ManikaSaini/zomato-restaurant-recommendation` on Hugging Face. The source is pinned to commit `5738e9eda2fad49ad51c6e0ed26e761d9b947133`. Do not commit the 574 MB source CSV; the Phase 1 adapter downloads and verifies the pinned source at ingestion time.

See [docs/data-profile.md](docs/data-profile.md) for the schema, limitations, and canonical mapping proposal.

## Configuration and secrets

Use environment variables and local `.env` files. `.env` files are ignored; only `.env.example` belongs in version control. Never place provider keys in web variables, source code, test snapshots, logs, or Docker images.

## Current scope

The Phase 1 data foundation, Phase 2 deterministic API, and Phase 3 grounded ranking layer provide:

- `GET /health/live` reports process health.
- `GET /health/ready` reports Phase 0 readiness and makes no dependency calls.
- The web app checks API liveness.
- Canonical normalization, quality reports, immutable PostgreSQL dataset versions, and atomic activation.
- Local fixture and pinned Hugging Face CSV adapters plus an operator CLI.
- Versioned recommendation and metadata routes with hard filtering, deterministic ranking,
  grounded template explanations, and transparent no-match relaxations.
- Provider-neutral LLM ranking with strict candidate membership, trusted-field rehydration,
  one bounded repair, circuit breaking, deterministic fallback, and privacy-safe audit metadata.

The default fake provider requires no key. Real provider credentials remain server-side and optional;
the API remains useful through deterministic fallback.
