# Phase 3 Baseline

- Dataset fixture: `docs/fixtures/restaurants_phase0.csv`
- Scoring version: `score-v1`
- Prompt version: `rank-v1`
- Model: `fake-grounded-v1`
- Evaluation type: deterministic automated baseline

## Hard gates

| Gate | Required | Automated assertion |
|---|---:|---:|
| Unknown restaurant rate after validation | 0% | 0% |
| Hard-constraint violation rate | 0% | 0% |
| Altered factual fields reaching the API | 0% | 0% |
| Fallback success with eligible candidates | 100% | 100% |
| Invalid schema bypass rate | 0% | 0% |

The suite injects malformed JSON, unknown IDs, duplicate IDs, extra factual fields, unsafe HTML,
prompt-like user text, provider failures, and timeouts. These values describe the expected automated
baseline encoded by the tests; record a dated executed report from CI before release. No live-provider
quality claim is made by this fake-model baseline.

## Human review rubric

Review each live-provider profile from 0–2 on relevance, evidence specificity, trade-off clarity,
caveat quality, and concision. Any unknown candidate, hard-constraint violation, altered fact, secret
disclosure, or unsupported claim is an automatic release failure regardless of the subjective total.
