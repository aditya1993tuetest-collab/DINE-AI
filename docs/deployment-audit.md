# Deployment audit

Audit date: 2026-10-23. This document records repository evidence, not a live-platform audit. Findings marked **resolved locally** were addressed during this review; deployment-dependent findings remain open.

## Current architecture

The application is a modular monolith split into two deployable services:

```text
Browser -> React/Vite static site -> FastAPI JSON API
                                      |-> PostgreSQL (restaurants, versions, audits)
                                      |-> Redis/Valkey (cache and fixed-window throttling)
                                      `-> Groq Chat Completions

Offline operator -> pinned Hugging Face CSV -> validation/normalization -> PostgreSQL activation
```

The request path never downloads the dataset. It queries one atomically activated dataset version in PostgreSQL, applies hard filters and deterministic ranking, sends at most 12 compact candidates to Groq, validates returned IDs/text, and rehydrates all restaurant facts from trusted database rows. Provider failure returns deterministic results.

## Verified technology stack

| Area | Repository evidence |
|---|---|
| Frontend | React 19.1.1, React DOM 19.1.1, TypeScript 5.9.2, Vite 7.1.4 |
| Frontend testing | Vitest 3.2.4, Testing Library 16.3.0, Playwright 1.64+, axe-core |
| Backend | Python `>=3.12,<3.15`, FastAPI `>=0.115,<1.0`, Uvicorn `>=0.34,<1.0`, Pydantic Settings `>=2.7,<3.0` |
| Persistence | SQLAlchemy 2.x, Alembic 1.x, psycopg 3.x, PostgreSQL-specific JSONB/UUID/index migrations |
| Cache/abuse control | Redis client 5.x/6.x; cache and anonymous fixed-window request throttling |
| LLM | Direct `httpx` call to Groq's OpenAI-compatible chat-completions endpoint |
| Container/runtime | Python 3.12 slim API image; Node 24 build plus unprivileged Nginx 1.27 web image |
| CI | GitHub Actions: lint, format, type check, tests, migrations, browser/a11y tests, secret/dependency/image scanning and SBOM |
| Languages | Python, TypeScript/TSX, SQL, shell, PowerShell, YAML, HTML/CSS |

Python dependencies use bounded ranges rather than a lock file. Frontend dependencies are reproducibly locked by `apps/web/package-lock.json`.

## API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/health/live` | Process liveness, dependency-free |
| GET | `/health/ready` | Database, active dataset, Redis requirement, and LLM-mode status; returns 503 when not ready |
| GET | `/metrics` | Prometheus text metrics |
| POST | `/api/v1/recommendations` | Validated, grounded recommendations |
| GET | `/api/v1/metadata/locations` | Active-dataset localities |
| GET | `/api/v1/metadata/cuisines` | Active-dataset cuisines |
| GET | `/api/v1/metadata/budgets` | Versioned budget profiles |
| GET | `/docs`, `/openapi.json` | FastAPI-generated API documentation |

## Dataset and storage audit

- Source: `ManikaSaini/zomato-restaurant-recommendation`, pinned to commit `5738e9eda2fad49ad51c6e0ed26e761d9b947133` with expected SHA-256 `4b0c91c37585310d509873dc399fdf739c7d222fcf7a693e4461b23d25a9d43d`.
- Verified source shape: one Bangalore dataset, 51,717 source rows, approximately 574 MB because of large review/menu fields.
- The ingestion CLI verifies revision/hash/schema, normalizes only serving fields, applies quality gates, de-duplicates, stages an immutable version, and atomically activates it.
- Large downloads now stream to a temporary file and are consumed row-by-row. The raw CSV is neither committed nor retained after ingestion.
- Serving tables intentionally require PostgreSQL; SQLite is not a production substitute because migrations use PostgreSQL UUID, JSONB, partial indexes, and array relationships.
- No new database is warranted. PostgreSQL is already a clear requirement for durable serving data and atomic dataset activation.
- The current Hugging Face page exposes the data but no explicit license in the visible dataset card. Permission to redistribute/use the data in a public application remains a non-code release decision.

## LLM audit

- The original example configuration selected `llama-3.3-70b-versatile`; the milestone requires `openai/gpt-oss-120b`. Local templates and the Render definition now use the milestone model. An existing untracked `.env` can still override this and must be checked manually without exposing its key.
- Groq currently lists `openai/gpt-oss-120b` as a production model with JSON Object Mode and a 131,072-token context. The adapter uses JSON Object Mode, temperature 0, low reasoning effort, hidden reasoning, a 700-token output cap, and a 12-candidate cap.
- Deterministic filtering/ranking occurs before the LLM. Candidate prompts contain only ID, name, locality/city, cuisines, rating/scale, and price/currency—not reviews, menus, addresses, or arbitrary source rows.
- Output guards reject unknown/duplicate IDs, extra factual copies, markup, malformed JSON, empty rankings, and excessive output. Trusted facts are never taken from the model.
- Transient/timeout/429/5xx responses receive one bounded retry; malformed output receives one bounded repair; a circuit breaker and deterministic fallback prevent provider failure from crashing requests.
- The milestone limits (30 RPM, 1,000 RPD, 8,000 TPM, 200,000 TPD) match Groq's currently published free-plan table, but the account's Limits page remains authoritative.

## Environment and build audit

- Server-only secrets: `DATABASE_URL`, `REDIS_URL`, and `LLM_API_KEY`.
- Browser-safe build variables: `VITE_API_BASE_URL` and `VITE_API_TIMEOUT_MS` only.
- `.env` and `.env.*` are ignored; `.env.example` is explicitly allowed. `.dockerignore` now prevents local secrets, virtual environments, caches, and raw data entering Docker build contexts.
- The frontend now defaults to same-origin `/api` paths. Vite and Nginx proxy local/container same-origin requests; split hosting sets `VITE_API_BASE_URL` at build time.
- Managed `postgresql://`/`postgres://` URLs are normalized to the installed psycopg 3 driver.
- The API container now includes Alembic files and has a production start script that honors platform `PORT`, worker count, graceful shutdown, and an optional migration step.
- The original CI oversized-file shell block was nested incorrectly under `upload-artifact` inputs. It is now part of the repository policy step.

## Issue register

| Priority | Finding | Impact | Disposition |
|---|---|---|---|
| Critical | Dataset license/redistribution terms are not declared on the visible source page | Public use may lack legal authorization | Open: obtain/record permission before public production |
| Critical | A deployed database has no active dataset until migrations and one ingestion complete | Metadata/recommendations are unavailable | Open operational step; readiness correctly returns 503 |
| High | Original browser fallback hardcoded `http://localhost:8000` | Production browser calls the user's machine | Resolved locally with same-origin default/build variable |
| High | API Docker image omitted Alembic files and ignored platform `PORT` | Managed deployment could not migrate/start portably | Resolved locally |
| High | Docker context did not exclude `.env`, venvs, caches, or raw data | Secret exposure and oversized/slow builds | Resolved locally |
| High | Free Render PostgreSQL expires after 30 days and has no backups | Demo data disappears; not production durable | Open platform constraint; use paid DB for real production |
| High | Readiness returned HTTP 200 while not ready | Orchestrators could route traffic before data was usable | Resolved locally with HTTP 503 and Redis state |
| High | Managed PostgreSQL URLs omit the SQLAlchemy psycopg driver qualifier | Runtime import/connection failure | Resolved locally |
| Medium | Full source was buffered in memory during ingestion | Likely memory pressure/OOM around a 574 MB CSV | Resolved locally with streamed download/parse |
| Medium | Production proxy address was not used for throttle identity | All users could share one proxy-derived quota | Resolved locally behind explicit `TRUST_PROXY_HEADERS` |
| Medium | Only one CORS origin was accepted | Preview/custom domains could not coexist | Resolved locally with a comma-delimited allowlist |
| Medium | Python dependencies are range-bounded, not lock-file pinned | Rebuilds may resolve newer compatible releases | Open; CI reduces but does not eliminate drift |
| Medium | Redis rate limiting fails open by design | An outage removes application-level throttling | Accepted for availability; edge/platform throttling remains advisable |
| Medium | Free API instances sleep after 15 idle minutes | First demo request can take about a minute | Open free-tier constraint; warm manually or use paid compute |
| Low | FastAPI shutdown event API emits a deprecation warning | Future framework upgrade maintenance | Open; behavior currently tested |
| Low | Two SQLAlchemy `distinct()` usages emit warnings under test | Future ORM compatibility concern | Open, not a current functional failure |

## Deployment readiness

The repository is locally deployment-prepared for a student demonstration, but it is **not yet live-production ready**. Code/build blockers found in this audit are resolved. Remaining gates are operational or external: commit/push the repository, create platform resources, configure secrets/URLs, migrate and ingest the pinned dataset, verify database size, confirm data-use permission, run live smoke tests, and choose a durable paid database/backup plan for use beyond a 30-day demonstration.

## Recommended approach

Use one Render Blueprint with a free static site, free Python/Docker web service, free Render Key Value, and free Render PostgreSQL for the milestone demonstration. Keep frontend and backend as separate services because the frontend is static/CDN-friendly while the API has stateful dependencies and secrets. Upgrade PostgreSQL (and preferably API compute) before describing the system as production-grade. See `docs/deployment-plan.md` and `DEPLOYMENT.md`.
