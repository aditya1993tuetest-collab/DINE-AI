# Phase 3 LLM Operations and Evaluation

Phase 3 keeps deterministic filtering authoritative. The model receives only the top configured
eligible candidates and can return only their IDs, explanations, caveats, and an optional summary.
All restaurant facts are rehydrated from PostgreSQL after validation.

## Provider configuration

Development defaults to `LLM_PROVIDER=fake`. To use Groq, place a newly rotated credential in an
ignored local `.env` or deployment secret manager:

```text
LLM_PROVIDER=groq
LLM_MODEL=<approved-groq-model-id>
LLM_API_KEY=<secret-manager-reference-or-local-secret>
```

Never commit, log, paste into prompts, or place provider keys in `VITE_*` variables. The application
does not include credentials, raw prompts, provider bodies, or raw free-form preferences in audits.

## Failure behavior

- Transient provider and timeout failures receive at most one bounded retry.
- Malformed output receives exactly one structured repair attempt.
- Unknown or duplicate IDs, factual copies, unsafe markup, unsupported claims, and excessive output
  are rejected.
- Persistent failure, oversized prompts, or an open circuit returns deterministic recommendations
  with `mode: fallback` and HTTP success.
- Database failure remains a service error; no ungrounded response is produced.

The circuit opens after `LLM_CIRCUIT_FAILURE_THRESHOLD` failed requests and probes again after
`LLM_CIRCUIT_COOLDOWN_SECONDS`. Readiness stays healthy when PostgreSQL and an active dataset are
available because fallback does not require the provider.

## Prompt rollback

Prompts are immutable under `docs/prompts/`. Set `ACTIVE_PROMPT_VERSION=rank-v1` to select the
approved version. A new prompt requires a new file, evaluation run, and baseline report; never edit
an approved prompt in place.

## Audits and retention

`recommendation_audits` stores request and version identifiers, a structured-query hash, candidate
and returned IDs, mode, duration, token counts, and a failure category. It excludes raw free-form
text. Production access is limited to operations and evaluation roles. Default retention is 30 days;
longer retention requires privacy approval. No automatic deletion job is enabled until that policy is
approved operationally.

## Offline release gates

Run the fake/adversarial suite and the versioned profiles in `docs/evals/phase3-profiles.json` before
provider or prompt promotion. Hard gates are:

- Unknown restaurant rate after validation: 0%.
- Hard-constraint violation rate: 0%.
- Altered factual fields reaching the API: 0%.
- Deterministic fallback success with eligible candidates: 100%.
- Schema validity after guard: 100% or deterministic fallback.

Human review scores ranking relevance, evidence use, trade-off clarity, caveat quality, and concision.
Record dataset, scoring, prompt, and model versions plus latency and token usage with every run.
