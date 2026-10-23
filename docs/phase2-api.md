# Phase 2 Deterministic Recommendation API

Phase 2 requires an active Phase 1 dataset and remains fully functional without an LLM. All routes
are versioned under `/api/v1`; costs are integers in minor currency units.

## Recommend

`POST /api/v1/recommendations`

```json
{
  "location": {"city": "Bangalore", "locality": "Indiranagar"},
  "budget": {"tier": "medium", "currency": "INR"},
  "cuisines": ["Italian", "Chinese"],
  "minimumRating": 4.0,
  "additionalPreferences": "quiet family dinner",
  "resultCount": 5
}
```

Location is required. Budget may be a named tier or an explicit `minimumMinor`/`maximumMinor`
range, never both. Only INR is supported because Phase 1 contains no verified currency conversions.
Cuisine matching requires at least one requested cuisine. Result count defaults to 5 and is capped
at 10; free-form preferences are capped at 500 characters and remain untrusted soft context.

The response reports the active dataset version, `score-v1`, normalized interpretations, and
grounded restaurant facts. Phase 3 may return `mode: llm`; provider failure returns `mode: fallback`
with deterministic explanations. An unverifiable free-form preference produces a caveat rather than
an unsupported claim.

When there is no exact match, `recommendations` is empty. The API independently counts locality,
budget, rating, and cuisine relaxations and returns only those with candidates. It never applies a
relaxation automatically.

## Metadata

- `GET /api/v1/metadata/locations?query=ind&limit=20`
- `GET /api/v1/metadata/cuisines?query=ital&limit=20`
- `GET /api/v1/metadata/budgets?currency=INR`

Search text is treated literally, including `%` and `_`, and is capped at 100 characters. Metadata
lists are bounded to 100 values and come only from the active dataset or versioned budget profiles.

## Errors and Request IDs

Clients may provide a safe `X-Request-ID`; otherwise the service generates one. It appears in both
the response header and body. Validation failures use `INVALID_PREFERENCE`; a missing active dataset
uses `DATASET_UNAVAILABLE`. Errors use this stable envelope:

```json
{
  "requestId": "e50a8f70-6d48-4a75-a8ad-4b58a06ec044",
  "error": {
    "code": "INVALID_PREFERENCE",
    "message": "The request is invalid.",
    "details": [{"field": "minimumRating", "reason": "less_than_equal"}]
  }
}
```

`GET /health/ready` checks database connectivity and an active dataset. It reports the LLM as
`degraded` without making the deterministic service unready.

Interactive OpenAPI documentation is available at `/docs`; the machine contract is `/openapi.json`.

Before release, run `scripts/explain-phase2.sql` against a representative active dataset and retain
the `EXPLAIN ANALYZE` output with the release evidence. The automated fixture suite also records a
two-second upper bound for the broad deterministic filter path; this is a regression guard, not a
production latency target.
