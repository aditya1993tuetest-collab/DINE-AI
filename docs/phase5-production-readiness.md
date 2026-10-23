# Phase 5 production readiness

## Runtime controls

Redis provides shared response/metadata caching and fixed-window anonymous rate limiting. Recommendation keys include dataset, scoring, prompt, model, normalized structured query, a SHA-256 free-text hash, and result count. Only schema-validated responses are cached; Redis failures are misses or rate-limit fail-open events. Defaults are 5 minutes for recommendations, 15 minutes for metadata, 20 recommendation requests/minute/IP hash, and 120 metadata requests/minute/IP hash.

The API enforces a 16 KiB request ceiling and the Pydantic contract enforces 500 free-text characters, ten cuisines, and ten results. Ingress must repeat the body/rate limits. Raw IPs, prompts, credentials, and free text are excluded from logs, metrics, traces, and cache keys.

## Environments and secrets

Development uses `.env`; staging and production use `/run/secrets` or the platform secret manager. Required production values are `DATABASE_URL`, `REDIS_URL`, `REDIS_REQUIRED=true`, `LLM_API_KEY`, `LLM_MODEL`, `WEB_ORIGIN`, and `TRUSTED_HOSTS`. Database roles are separated operationally: migration owns DDL, API receives SELECT/INSERT only for serving/audits, ingestion receives version and restaurant writes, and audit readers receive SELECT on audit metadata only.

Only PostgreSQL, Redis, DNS, the OTLP collector, and `api.groq.com:443` should be reachable from API workloads. TLS terminates at managed ingress; HSTS is added there after domain validation. Application and static-host responses add CSP, frame, MIME, referrer, and permissions headers.

## Reliability and objectives

- Availability target: 99.9% monthly API success excluding invalid and rate-limited requests.
- Warm-cache p95: 300 ms; deterministic uncached p95: 1 s; Groq end-to-end p95: 5 s.
- RPO: 15 minutes using managed PostgreSQL PITR; RTO: 60 minutes.
- Provider timeout: 4 seconds with a bounded repair attempt and circuit breaker. Provider failure returns deterministic fallback.
- Redis failure disables cache/rate sharing but does not block recommendations. Database/no-active-dataset failure returns `DATASET_UNAVAILABLE`.
- Database pool defaults to 10 plus 10 overflow per instance with a 5-second acquisition timeout. Size total connections against the managed database before scaling.

## Validation commands

Run the normal CI suite, then in an isolated staging environment:

```text
nextleap-load --url https://staging.example --requests 500 --concurrency 20
sh scripts/backup.sh
sh scripts/restore-test.sh /secure-backups/nextleap-TIMESTAMP.dump
```

Exercise four load profiles: common cached, broad uncached, no-match, and maximum legal request. Record p50/p95/p99, error/fallback/cache rates, database slow-query output, Groq token usage, and cost. The load utility has hard ceilings of 10,000 requests and 100 workers. Never target production without written authorization.

## Retention and cost

Keep request logs 14 days, traces 7 days, aggregate metrics 13 months, recommendation audits 30 days, and immutable dataset versions for 90 days while retaining the active and two prior versions. Backups follow the managed provider's PITR policy and are encrypted. Cleanup is a reviewed job; activation never deletes datasets.

Groq spend alerts are configured in the provider console at 50%, 80%, and 100% of the monthly budget. Dashboard cache-hit and avoided-call metrics quantify savings; audit metadata records model/version and token/cost fields when available, never prompt text.

## External evidence still required

CI/CD definitions and rehearsal procedures are included, but staging deployment, managed backup/PITR enablement, restore evidence, provider budget alerts, load evidence, and canary rollback evidence require actual platform credentials and an isolated staging environment. They cannot be truthfully claimed from a local repository alone.
