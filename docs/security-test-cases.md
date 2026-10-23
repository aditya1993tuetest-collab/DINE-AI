# Phase 5 security test cases

These cases run only against isolated test or staging systems.

1. Submit SQL metacharacters in city, locality, cuisines, and metadata query; expect normal empty/validation behavior and unchanged schema.
2. Submit HTML/script/event-handler payloads in free text and mocked model explanations; expect escaped text, no DOM nodes, and CSP enforcement.
3. Submit prompt instructions asking for candidates outside the supplied IDs, secrets, system prompts, or fabricated facts; expect guard rejection and deterministic fallback.
4. Send bodies above 16 KiB, more than ten cuisines/results, text above 500 characters, malformed JSON, and slow/partial requests; expect 413/422 at edge/application without provider calls.
5. Exceed metadata and recommendation rate limits independently from two API replicas; expect consistent 429 envelopes and `Retry-After` from shared Redis.
6. Inject request IDs containing CRLF or more than 100 characters; expect generated safe IDs.
7. Disable Redis and Groq independently and together; expect cache misses/rate fail-open plus deterministic fallback, with no unhandled error.
8. Remove the active dataset or database connectivity; expect readiness `not_ready` and safe `DATASET_UNAVAILABLE` responses.
9. Search logs, metrics, traces, SBOM, images, browser artifacts, and cache keys for API keys and raw free text; expect no matches.
