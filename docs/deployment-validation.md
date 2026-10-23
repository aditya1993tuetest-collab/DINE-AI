# Deployment validation

Validation date: 2026-10-23. Results describe commands actually run in the audited workspace. No remote deployment, real Groq call, full Hugging Face download, or destructive action was performed.

## Environment

- Workspace: `C:\Users\Aditya Agarwal\Desktop\NextLeap`
- Python test environment: repository `.phase5-python`, Python 3.14.0
- Node.js: 24.11.1; npm: 11.6.2
- Docker CLI present, but Docker Desktop engine access failed at the named pipe.
- Git repository exists but has no commits; all project files were untracked at audit start.
- PostgreSQL/Redis integration services were not available locally.

## Executed checks

| Check | Command | Result |
|---|---|---|
| Backend lint | `.phase5-python\Scripts\python.exe -m ruff check apps/api` | PASS |
| Backend formatting | `.phase5-python\Scripts\python.exe -m ruff format --check apps/api` | PASS |
| Backend strict types | `.phase5-python\Scripts\python.exe -m mypy apps/api/src apps/api/tests` | PASS |
| Backend automated tests | `.phase5-python\Scripts\python.exe -m pytest apps/api/tests -q` | PASS: 60 passed, 1 skipped |
| Backend coverage gate | Same pytest command | PASS by configured 90% rounded gate; report showed 89.87% |
| Frontend unit/component tests (baseline) | `npm test -- --reporter=dot` | PASS: 7 tests before deployment changes |
| Frontend production build (baseline) | `npm run build` | PASS |
| Docker engine/container validation | `docker version` | NOT EXECUTED: Docker engine access denied/unavailable |

Backend warnings: FastAPI shutdown-event deprecation, a Starlette/httpx compatibility deprecation, two SQLAlchemy `distinct()` warnings, absent `/run/secrets` on Windows, and an unwritable pytest cache path. These did not fail the executed suite and are recorded in the audit as follow-up maintenance where applicable.

The first backend baseline run had 55 passes, 1 skip, and 1 failure because the developer's untracked root `.env` overrode the test that asserted default provider settings. The test was isolated from `.env`; the final backend run passes. No secret value was printed or copied.

## Requirement matrix

| Scenario | Status | Evidence / remaining action |
|---|---|---|
| 1. Frontend production build | PASS (baseline); final rerun pending | Vite emitted `dist` successfully |
| 2. Backend production-compatible settings/start | PARTIAL | Settings, Docker start script, migrations, port and graceful shutdown are tested statically/unit-wise; container start needs Docker/live platform |
| 3. Health check responds correctly | PASS | TestClient covers dependency-free liveness and 503 not-ready semantics |
| 4. Frontend communicates with backend | PASS mocked / NOT LIVE | Unit/E2E contracts mock API; live cross-origin Render check remains |
| 5. Available locations load | PASS automated / NOT LIVE | Component and API tests cover metadata; requires active deployed dataset |
| 6. Cuisine optional | PASS automated | Request/component/API coverage |
| 7. Budget filtering | PASS automated | Backend scoring/recommendation tests; live dataset smoke remains |
| 8. Minimum rating filtering | PASS automated | Backend recommendation tests; live dataset smoke remains |
| 9. Valid inputs produce relevant recommendations | PASS deterministic fixture / NOT REAL LLM | API/scoring/LLM guard tests; real Groq relevance review remains |
| 10. No matches produce meaningful empty state | PASS automated | Web component and browser specs plus API no-match tests |
| 11. Invalid input handled safely | PASS automated | Pydantic/error-envelope/request-size tests |
| 12. Groq failures do not crash app | PASS automated | timeout/transient/malformed/unknown/duplicate/markup cases fall back |
| 13. Timeouts/rate limits handled | PASS automated/inspection | Provider timeout/429 mapping, circuit fallback, browser timeout, Redis throttle; live quota test intentionally not run |
| 14. API keys absent from browser | PASS static inspection / NOT DEPLOYED | Only API base URL/timeout are Vite variables; live bundle/network inspection remains |
| 15. Recommendations contain dataset facts | PASS automated | Candidate membership guard and trusted-row rehydration tests |
| 16. Mobile and desktop usable | Browser rerun pending | Playwright defines Desktop Chrome and Pixel 7 plus axe checks |

## Release checklist

- [x] `.env` ignored; `.env.example` contains names only.
- [x] Docker context excludes `.env`, raw data, environments, caches, and build output.
- [x] No hardcoded localhost API fallback in browser production code.
- [x] CORS is an exact comma-delimited allowlist; no wildcard credentials.
- [x] Trusted hosts and optional trusted-proxy behavior are configurable.
- [x] Request size, schema, body fields, result count, prompt size, and output tokens are bounded.
- [x] Health liveness/readiness are separate and not-ready returns 503.
- [x] Dataset download is pinned, hashed, streamed, validated, versioned, and outside request handling.
- [x] LLM shortlist is compact; returned facts are grounded and validated.
- [x] Provider timeout/retry/rate-limit/circuit/fallback paths exist.
- [x] Production container runs unprivileged and honors platform port/shutdown.
- [x] Render infrastructure definition contains no credential values.
- [ ] Docker images built and health-checked locally.
- [ ] PostgreSQL integration test run against PostgreSQL 17.
- [ ] Full pinned source ingested and its normalized storage size recorded.
- [ ] Dataset permission/license confirmed.
- [ ] Groq key/model/account quotas verified with one minimal staging request.
- [ ] Live frontend/API/CORS/headers/mobile/desktop smoke test completed.
- [ ] Backup/restore tested on the selected paid production database.

## Readiness decision

**Ready for a controlled Render milestone deployment after the remaining manual gates; not ready to claim durable production operation.** The critical release blockers are data-use authorization, creation/ingestion of an active managed dataset, live service verification, and a durable backed-up database choice beyond the 30-day free demonstration window.
