# Evaluation Plan

## 1. Purpose

This document defines how to evaluate the AI-powered restaurant recommendation system throughout development and before release. It operationalizes the quality, grounding, reliability, performance, security, and usability requirements in [implementation-plan.md](implementation-plan.md), [architecture.md](architecture.md), [problemStatement.md](problemStatement.md), and [edge-case.md](edge-case.md).

The evaluation program answers five questions:

1. Does the system always honor explicit user constraints?
2. Are every restaurant and factual value grounded in the selected dataset version?
3. Does ranking improve the usefulness of the eligible candidate list?
4. Are explanations specific, supported, clear, and appropriately caveated?
5. Does the complete product remain reliable, secure, responsive, accessible, and affordable under expected and adverse conditions?

Evaluation is a release gate, not only an exploratory activity. Every run must be reproducible from versioned inputs and produce machine-readable results.

## 2. Evaluation Principles

### 2.1 Correctness Before Preference

A fluent or appealing response is not acceptable if it violates a hard constraint, names an unknown restaurant, alters a factual field, or presents an unsupported claim as fact.

### 2.2 Separate Deterministic and Generative Quality

Evaluate these layers independently:

- Data ingestion and normalization.
- Preference validation and normalization.
- Hard filtering.
- Deterministic scoring.
- LLM ranking.
- Explanation generation.
- Response validation and factual rehydration.
- API and web presentation.
- Operational behavior.

An end-to-end score must not hide a defect in a lower layer.

### 2.3 Evaluate Against Frozen Versions

Every evaluation run must record:

- Application commit or artifact digest.
- Dataset source revision and active dataset version.
- Evaluation-set version.
- Schema version.
- Budget-profile version.
- Scoring-configuration version.
- Prompt version.
- LLM provider and model identifier.
- Model parameters.
- Evaluator rubric and judge version.
- Runtime environment and timestamp.

### 2.4 Prefer Executable Assertions

Use deterministic code for membership, filtering, factual consistency, schema, and latency calculations. Human or model judges should evaluate only qualities that cannot be reliably determined from structured data, such as relative usefulness or clarity.

### 2.5 Preserve Failure Evidence Safely

Store case IDs, structured inputs, candidate IDs, outputs, scores, and failure labels. Do not store production free-form user text unless retention has been explicitly approved.

## 3. Evaluation Levels

| Level | Subject | Primary purpose | Typical cadence |
|---|---|---|---|
| L0 | Functions and domain rules | Validate parsing, filters, scoring, and guards | Every change |
| L1 | Components and contracts | Validate database, cache, provider, and API boundaries | Every pull request |
| L2 | Offline recommendation suite | Compare scoring, prompt, and model behavior | Every relevant change |
| L3 | End-to-end product | Validate complete user flows and presentation | Every release candidate |
| L4 | Performance, resilience, and security | Validate behavior under stress and failure | Scheduled and before release |
| L5 | Production monitoring and experiments | Detect drift and measure real-world quality | Continuous after launch |

## 4. Non-Negotiable Invariants

These are binary gates. A single confirmed violation blocks release unless the affected feature is removed or the issue is formally resolved.

| ID | Invariant | Required target |
|---|---|---:|
| INV-01 | Every returned restaurant ID belongs to the request's candidate set | 100% |
| INV-02 | Every returned restaurant satisfies all hard constraints or is explicitly labeled as an accepted relaxation | 100% |
| INV-03 | Name, location, cuisines, rating, cost, and currency match the trusted record | 100% |
| INV-04 | Unknown restaurant IDs reach the user | 0 |
| INV-05 | Missing facts are fabricated | 0 |
| INV-06 | Silent constraint relaxation occurs | 0 |
| INV-07 | Invalid LLM output bypasses response validation | 0 |
| INV-08 | Provider failure prevents deterministic results when eligible candidates exist | 0 |
| INV-09 | Failed ingestion changes the active dataset | 0 |
| INV-10 | Secrets or raw credentials appear in client artifacts, responses, logs, traces, or evaluation reports | 0 |

## 5. Evaluation Dataset Strategy

### 5.1 Dataset Types

Maintain four distinct evaluation datasets.

#### A. Synthetic Rule Fixture

A small, hand-authored restaurant dataset with exact expected outcomes. It should cover:

- Multiple cities and localities.
- Single and multiple cuisines.
- Cost values below, at, and above budget boundaries.
- Ratings below, at, and above thresholds.
- Missing rating, cost, cuisine, and locality.
- Multiple currencies and incompatible cost bases.
- Duplicate and conflicting records.
- Unicode, long text, HTML-like text, and prompt-injection content.
- Zero, one, fewer-than-requested, exact, and excessive candidate counts.

Use it for fast deterministic and adversarial assertions.

#### B. Frozen Source Snapshot

A pinned, approved snapshot of the real Hugging Face dataset. Use it to evaluate representative distribution, query performance, normalization coverage, and recommendation realism. The snapshot must be referenced by revision and content hash.

#### C. Curated Recommendation Set

A versioned collection of user profiles with expected constraints, candidate properties, and human relevance judgments. It should contain standard, difficult, ambiguous, no-match, and unsupported-preference scenarios.

#### D. Adversarial and Failure Set

Cases derived from [edge-case.md](edge-case.md), including malformed input, injection attempts, provider errors, invalid model output, cache corruption, data drift, and concurrency failures.

### 5.2 Evaluation Case Schema

Each offline case should use a structure equivalent to:

```json
{
  "caseId": "REC-BUDGET-001",
  "category": "standard",
  "datasetVersion": "fixture-v1",
  "query": {
    "location": {"city": "Bangalore", "locality": null},
    "budget": {"maximumMinor": 150000, "currency": "INR"},
    "cuisines": ["Italian"],
    "minimumRating": 4.0,
    "additionalPreferences": "A relaxed family dinner",
    "resultCount": 5
  },
  "expected": {
    "eligibleRestaurantIds": ["r-101", "r-102"],
    "ineligibleRestaurantIds": ["r-103"],
    "requiredFacts": ["location", "cuisine", "budget", "rating"],
    "unsupportedPreferences": ["relaxed", "family suitability"],
    "expectedModeWhenLlmFails": "fallback"
  },
  "tags": ["budget-boundary", "unsupported-soft-preference"]
}
```

Exact expected ranking is appropriate for deterministic fixtures. For subjective LLM ordering, store relevance grades or pairwise preferences rather than asserting one perfect total order.

### 5.3 Coverage Dimensions

The curated suite must cover combinations across:

| Dimension | Required coverage |
|---|---|
| Location | Supported city, unsupported city, exact locality, missing locality, alias, conflicting city/locality |
| Budget | No budget, tier, explicit range, exact boundary, missing source cost, wrong currency, conflicting tier/range |
| Cuisine | None, single, multiple, unknown, alias, multi-cuisine restaurant, missing source cuisine |
| Rating | None, minimum, maximum, exact boundary, missing source rating, low-vote high rating |
| Free text | Empty, supported attribute, unsupported preference, conflict, injection attempt, excessive length |
| Candidate count | 0, 1, below requested, exactly requested, above LLM limit, above database limit |
| LLM behavior | Valid, malformed, refusal, unknown ID, duplicates, unsupported claims, timeout, rate limit |
| Data quality | Complete, partially missing, malformed, duplicate, Unicode, unsafe text |
| User interface | Desktop, mobile, keyboard, screen reader, slow network, stale response |
| Operations | Cache hit/miss, cache outage, DB outage, dataset activation, rolling deployment, rollback |

### 5.4 Split Policy

Use three non-overlapping sets:

- **Development set:** visible to engineers for prompt and scoring iteration.
- **Regression set:** visible inputs with locked expected properties; runs in CI.
- **Holdout set:** controlled by designated evaluators and used for release approval.

Do not tune prompts or weights directly against holdout outputs. Refresh the holdout periodically and whenever evidence suggests contamination.

## 6. Deterministic Evaluation

### 6.1 Ingestion Metrics

| Metric | Definition | Purpose |
|---|---|---|
| Parse success rate | Accepted raw rows / total raw rows | Detect parser regressions |
| Rejection rate | Rejected rows / total raw rows | Monitor data-quality impact |
| Duplicate rate | Duplicate rows / total raw rows | Track source and deduplication behavior |
| Required-field coverage | Records with field / accepted records | Verify usability of location/name/etc. |
| Comparable-cost coverage | Records with valid amount and currency / accepted records | Quantify budget-filter coverage |
| Valid-rating coverage | Records with valid rating and scale / accepted records | Quantify rating-filter coverage |
| Normalization stability | Records whose canonical identity remains stable across rerun / comparable records | Detect unintended identity churn |
| Publication atomicity | Failed publications changing active version | Must remain zero |

Thresholds for coverage and row-count drift should be based on the Phase 0 data profile. A large deviation requires review even when parsing technically succeeds.

### 6.2 Input Validation Metrics

- Acceptance rate for valid boundary inputs.
- Rejection rate for invalid boundary inputs.
- Field-level error accuracy.
- Consistency between browser and server validation.
- Maximum body and text-limit enforcement.
- Normalization equivalence for approved aliases and formatting variants.

Target: every contract fixture receives the expected normalized query or stable validation code.

### 6.3 Filtering Metrics

#### Hard-Constraint Compliance

```text
hard_constraint_compliance =
  returned_items_satisfying_all_hard_constraints / returned_items
```

Required target: `1.0` for every successful exact-match request.

#### Candidate Recall

For synthetic fixtures with a known eligible set:

```text
candidate_recall =
  returned_eligible_candidates / all_expected_eligible_candidates_within_limit
```

When a configured bound truncates candidates, evaluate whether the pre-ranking selection follows the documented order rather than expecting all eligible rows.

#### Candidate Precision

```text
candidate_precision =
  correctly_eligible_candidates / all_candidates_returned_by_filter
```

Required target: `1.0`.

### 6.4 Deterministic Ranking Metrics

- Stable ordering across identical requests and application instances.
- Score range compliance: all component and final scores are within documented bounds.
- Tie-breaker correctness.
- Monotonicity where applicable; for example, increasing a hard rating threshold must not introduce a lower-rated item.
- Top-K agreement against curated relevance grades.
- NDCG@K for graded relevance.
- Mean Reciprocal Rank when a case defines one preferred best result.
- Pairwise accuracy for restaurant pairs with a documented preference.

The deterministic scorer is the baseline against which LLM ranking must be compared.

### 6.5 Relaxation Accuracy

For each proposed relaxation:

- Re-run the independently modified query.
- Confirm the stated candidate count.
- Confirm that only the named constraint changed.
- Confirm the original response contains no relaxed recommendation.
- Confirm unsupported currency or missing data is not made eligible accidentally.

Required target: 100% accuracy for proposal definitions and counts on frozen evaluation data.

## 7. LLM Grounding Evaluation

### 7.1 Membership Accuracy

```text
membership_accuracy =
  valid_returned_ids / all_model_returned_ids
```

Measure both raw model behavior and post-guard API behavior:

- Raw membership rate helps compare prompts and models.
- Post-guard membership rate must be 100%.

### 7.2 Factual Consistency

For each displayed factual field:

```text
factual_consistency =
  facts_equal_to_trusted_record / displayed_factual_fields
```

The post-guard target is 100%. The system achieves this by rehydrating facts rather than trusting repeated model values.

### 7.3 Unsupported-Claim Rate

An unsupported claim is a factual assertion not justified by a supplied candidate attribute. Examples include claiming a restaurant is quiet, child-friendly, fast, romantic, currently open, or available for booking without supporting evidence.

```text
unsupported_claim_rate =
  recommendations_with_one_or_more_unsupported_claims / recommendations_reviewed
```

Required post-validation target: 0%. When an unsupported preference is relevant, the response should contain a caveat rather than an assertion.

### 7.4 Caveat Recall

```text
caveat_recall =
  unsupported_requested_preferences_correctly_caveated /
  unsupported_requested_preferences
```

Initial release target: at least 95% on the curated suite, with no critical unsupported claim presented as verified. Raise the target as the rubric and validator mature.

### 7.5 Structured-Output Validity

Track:

- First-pass schema-valid rate.
- Repair-attempt rate.
- Repair-success rate.
- Fallback rate due to invalid output.
- Duplicate-ID rate.
- Unknown-ID rate.
- Result-count violation rate.

Post-guard invalid structured output reaching clients must remain zero.

### 7.6 Prompt-Injection Resistance

Test injections in:

- Free-form user preferences.
- Restaurant names.
- Cuisine labels.
- Optional dataset attributes.
- Text that attempts to reveal prompts, credentials, or internal configuration.
- Text that requests external restaurants or constraint removal.

A case passes only when eligibility remains unchanged, no secret/system content is disclosed, every returned ID is valid, and explanations remain grounded.

## 8. Ranking Relevance Evaluation

### 8.1 Relevance Grades

Use a four-level rubric for each eligible restaurant relative to the query:

| Grade | Meaning |
|---:|---|
| 3 | Excellent fit across the most important stated preferences |
| 2 | Good fit with a minor trade-off |
| 1 | Eligible but weak fit compared with available alternatives |
| 0 | Not eligible or irrelevant; should never appear in exact results |

Grade 0 due to hard-constraint violation is a correctness failure, not merely low relevance.

### 8.2 Ranking Metrics

Use:

- **NDCG@3 and NDCG@5:** graded ordering quality.
- **Precision@K:** proportion of top results graded 2 or 3.
- **MRR:** how early the first grade-3 option appears.
- **Pairwise preference accuracy:** agreement with adjudicated human preference pairs.
- **Top-K overlap:** comparison between model/configuration versions.
- **Win/tie/loss against deterministic baseline:** judged per query.

### 8.3 LLM Value Gate

The LLM layer should not ship merely because it generates explanations. On the holdout set it should:

- Preserve every deterministic correctness invariant.
- Achieve no statistically or practically significant relevance regression against deterministic ranking.
- Demonstrate a net win in human-rated usefulness or explanation quality.
- Stay within agreed latency and cost budgets.

If it does not meet this gate, ship deterministic ranking with safe template explanations and continue evaluating the LLM layer separately.

## 9. Explanation-Quality Rubric

Evaluate each explanation on five dimensions using a 0-2 scale.

### 9.1 Evidence Alignment

| Score | Definition |
|---:|---|
| 0 | Contains an unsupported or contradictory claim |
| 1 | Mostly supported but vague or omits important evidence |
| 2 | Every material claim maps clearly to supplied facts or is labeled as inference/caveat |

### 9.2 Preference Coverage

| Score | Definition |
|---:|---|
| 0 | Does not address the user's meaningful preferences |
| 1 | Addresses some preferences but misses an important supported factor |
| 2 | Addresses the most important supported preferences and flags unsupported ones |

### 9.3 Specificity

| Score | Definition |
|---:|---|
| 0 | Generic praise that could describe any restaurant |
| 1 | Mentions one relevant attribute |
| 2 | Connects multiple concrete attributes to the user's request concisely |

### 9.4 Trade-Off Clarity

| Score | Definition |
|---:|---|
| 0 | Hides or contradicts a material limitation |
| 1 | Mentions a limitation unclearly |
| 2 | Clearly states important trade-offs and unverifiable preferences |

### 9.5 Readability

| Score | Definition |
|---:|---|
| 0 | Confusing, unsafe, unprofessional, or excessively verbose |
| 1 | Understandable with minor style issues |
| 2 | Concise, natural, and easy to compare with other results |

### 9.6 Explanation Score

```text
explanation_score =
  evidence_alignment
  + preference_coverage
  + specificity
  + tradeoff_clarity
  + readability
```

Maximum score: 10.

Proposed initial release gate:

- Mean score at least 8.0 on the holdout set.
- Evidence Alignment must equal 2 for every released sample.
- No sample may score 0 on Trade-Off Clarity due to a hidden unsupported preference.

Calibrate the non-safety threshold after an initial blinded annotation round. Safety and grounding requirements remain non-negotiable.

## 10. Human Evaluation Protocol

### 10.1 Evaluator Preparation

- Provide the query, candidate facts, system output, and rubric.
- Hide model/provider identity and configuration when comparing variants.
- Randomize variant order.
- Train evaluators on positive and negative examples.
- Include calibration cases before scored work.

### 10.2 Annotation Tasks

Evaluators should:

1. Mark any hard-constraint violation.
2. Mark unsupported or contradictory claims.
3. Grade candidate relevance.
4. Score each explanation dimension.
5. Select the more useful response in pairwise comparisons.
6. Record a concise reason using predefined labels plus optional notes.

### 10.3 Sampling and Agreement

- Use at least two independent evaluators for holdout cases.
- Send disagreements on correctness or unsupported claims to adjudication.
- Measure Cohen's kappa for two evaluators or Fleiss' kappa/Krippendorff's alpha for larger panels.
- Investigate low agreement before treating subjective scores as a release gate.
- Report confidence intervals for aggregate relevance comparisons.

### 10.4 Bias Review

Segment results by available dataset dimensions such as city, locality coverage, cuisine, price band, rating availability, and language. The goal is to find quality disparities caused by data coverage or ranking behavior, not to infer unsupported demographic attributes.

## 11. Automated Judge Use

An LLM judge may assist with explanation relevance, clarity, or rubric pre-labeling, but it must not be the sole authority for release.

Controls:

- Use deterministic code for all factual and eligibility checks.
- Version the judge model and prompt.
- Give the judge only the query, trusted candidate facts, output, and rubric.
- Require structured judge output with evidence spans or field references.
- Calibrate judge results against human-labeled cases.
- Track agreement and systematic bias.
- Manually review all alleged critical grounding failures and a sample of passes.
- Never let the evaluated model grade itself without independent validation.

## 12. API and Contract Evaluation

Evaluate:

- Request schema boundaries and unknown fields.
- Stable normalization and error codes.
- Successful, no-match, fallback, and failure response schemas.
- OpenAPI conformance.
- Result-count limits.
- Dataset, scoring, prompt, and mode metadata.
- Request-ID propagation.
- Absence of stack traces and provider-specific error bodies.
- Backward compatibility during rolling deployment.

Required release target: every versioned contract fixture passes against both the API schema and a deployed staging instance.

## 13. Web and Accessibility Evaluation

### 13.1 Functional Journeys

Automate these browser paths:

- Valid recommendation request.
- Missing optional preferences.
- Client validation error.
- Server validation error.
- No exact match and relaxation display.
- LLM fallback display.
- Metadata lookup failure with recoverable input.
- Slow request and cancellation.
- Stale response arriving after a newer request.
- Unknown server error code.

### 13.2 Presentation Assertions

- Facts, generated explanations, and caveats are distinguishable.
- Unavailable rating and cost are not displayed as zero.
- Currency formatting does not alter the underlying amount.
- Relaxed results cannot be mistaken for exact matches.
- Source-data freshness limitations remain visible.
- Generated text is never rendered as raw HTML.

### 13.3 Accessibility Gates

- Automated accessibility scan has no critical or serious violations in core flows.
- All interactions work with keyboard only.
- Focus is managed after validation and result loading.
- Form fields are named and errors are programmatically associated.
- Async status is announced without excessive repetition.
- Rating and cost have textual equivalents.
- Content reflows at 200% and 400% zoom without loss of function.
- Core flow passes manual smoke testing with designated screen-reader/browser combinations.

## 14. Performance and Scalability Evaluation

### 14.1 Workload Profiles

Test at least:

- Narrow query with few candidates.
- Typical query with moderate candidates.
- Broad query reaching the database candidate ceiling.
- No-match query requiring relaxation counts.
- Cache hit.
- Cache miss with LLM success.
- Cache miss with provider timeout and fallback.
- Metadata autocomplete burst.
- Ingestion running concurrently with online traffic.
- Sudden traffic spike and sustained load.

### 14.2 Metrics

- End-to-end latency at p50, p95, and p99.
- Non-LLM processing latency.
- Database query latency and rows examined.
- LLM latency and timeout rate.
- Response-validation latency.
- Throughput and error rate.
- CPU, memory, connection-pool, and event-loop/thread saturation.
- Cache hit rate and cache-operation latency.
- Queue or lock wait time when request coalescing is used.
- Prompt, completion, and total token counts.
- Estimated provider cost per successful recommendation.

### 14.3 Initial Performance Gates

The architecture proposes the following initial targets, subject to validation under production-like load:

- p95 non-LLM processing below 500 ms.
- p95 complete response below 6 seconds under normal provider conditions.
- No unbounded growth in memory or open connections during sustained load.
- Candidate and token ceilings are always enforced.
- Deterministic fallback completes within its separate agreed latency budget.

Record the exact load model, dataset size, instance sizing, geographic setup, and provider conditions with every result.

## 15. Reliability and Failure Evaluation

Inject failures at each boundary:

| Failure | Required result |
|---|---|
| Hugging Face unavailable | Ingestion fails safely; active version remains unchanged |
| Ingestion interrupted | Staging remains non-active and rerun is safe |
| Dataset activation races | Exactly one version becomes active |
| PostgreSQL unavailable | Readiness fails; requests stop within bounded timeout |
| Redis unavailable | Requests continue as cache misses where capacity permits |
| LLM timeout or outage | Eligible requests receive deterministic fallback |
| Malformed model response | One bounded repair at most, then fallback |
| Audit/telemetry sink unavailable | Core response follows documented noncritical behavior |
| API instance terminates | Graceful drain or safe retry without corrupted state |
| Provider recovers after outage | Jitter/circuit breaker prevents a retry storm |
| Disk or memory pressure | System fails safely and alerts before data corruption |
| Backup restore | Restored environment reaches a consistent active dataset |

Measure recovery time, error count, fallback success, resource cleanup, and alert delivery.

## 16. Security Evaluation

### 16.1 Required Test Areas

- SQL injection in all structured and metadata fields.
- Reflected and stored cross-site scripting.
- Prompt injection from user and dataset text.
- Oversized requests and model outputs.
- Log forging and control-character injection.
- Secret scanning of source, images, web bundles, logs, traces, and reports.
- CORS, trusted-proxy, and forwarding-header configuration.
- Least-privilege database roles.
- Rate-limit bypass attempts.
- SSRF/path traversal opportunities in ingestion and configuration.
- Dependency and container vulnerability scanning.
- Untrusted links or HTML in model output.

### 16.2 Security Release Gate

- No unresolved critical vulnerability.
- No unresolved high vulnerability without explicit time-bounded risk acceptance.
- No secret exposure.
- No route from model output to database/tool execution.
- No injection case may alter hard filters or response membership.
- Abuse tests must demonstrate bounded request size, candidate count, token count, and rate.

## 17. Cost Evaluation

### 17.1 Per-Request Cost

Record:

- Input tokens.
- Output tokens.
- Provider/model pricing version.
- Number of attempts and repairs.
- Cache result.
- Execution mode.
- Estimated cost.

```text
estimated_request_cost =
  input_tokens * input_unit_price
  + output_tokens * output_unit_price
```

### 17.2 Aggregate Projections

Project cost at expected, peak, and stress traffic using measured cache hit rate, fallback rate, and retry rate. Include ingestion, observability, database, cache, and hosting costs separately from model inference.

### 17.3 Cost Gates

The product owner must set absolute budgets before production. At minimum:

- Candidate and output-token limits are enforced.
- Unexpected retry/repair amplification is measured.
- Cost per successful LLM-mode request does not exceed the approved ceiling.
- Cache savings do not compromise freshness or correctness.
- Quota exhaustion has an alert and deterministic fallback.

## 18. Production Evaluation

### 18.1 Continuous Quality Signals

Monitor:

- Hard-constraint and response-guard rejection counts.
- Fallback and repair rates.
- No-match and relaxation rates.
- Latency and error rates by execution mode.
- Candidate count distributions.
- Cache hit rate.
- Token and cost distributions.
- Dataset-version changes in coverage and outcomes.
- User retry, reformulation, and result-selection signals when privacy policy allows.

Operational signals diagnose potential quality issues but do not replace curated evaluation.

### 18.2 Safe Feedback Collection

If feedback is implemented, collect simple usefulness signals and optional categorized reasons such as:

- Results did not match cuisine.
- Results were too expensive.
- Location was wrong.
- Explanation was not useful.
- Important preference was ignored.
- Information appeared incorrect.

Do not treat a single click as objective relevance truth. Analyze aggregated feedback alongside constraints and dataset coverage.

### 18.3 Drift Detection

Trigger review when:

- Source schema or coverage changes materially.
- No-match rate shifts after dataset activation.
- Model invalid-output or unsupported-claim rate rises.
- Relevance scores decline in scheduled regression runs.
- Latency, token use, or cost shifts without an application change.
- Provider behavior changes under the same model identifier.

## 19. Evaluation Run Workflow

### 19.1 Before the Run

1. Pin all application, data, prompt, model, and rubric versions.
2. Select development, regression, or holdout suite.
3. Verify fixture integrity and expected active dataset.
4. Validate provider quota and evaluation budget.
5. Create a unique run ID.

### 19.2 Execute

1. Run deterministic assertions.
2. Run each generative case for the configured repeat count.
3. Validate and store raw structured outputs securely.
4. Calculate automatic metrics.
5. Queue the required blinded human annotations.
6. Run adversarial and failure cases.
7. Capture performance and cost metadata.

### 19.3 Analyze

1. Compare invariant metrics with hard gates.
2. Compare relevance against baseline and prior release.
3. Segment results by coverage dimensions.
4. Review every grounding or security failure individually.
5. Inspect latency and cost regressions.
6. Calculate confidence intervals where appropriate.

### 19.4 Decide

Classify the run:

- **Pass:** all hard gates and approved soft thresholds pass.
- **Conditional pass:** only explicitly accepted noncritical regressions remain, with owner and expiry.
- **Fail:** any invariant, security, grounding, fallback, or required quality gate fails.

### 19.5 Archive

Store:

- Run manifest.
- Aggregate and per-case metrics.
- Failure list.
- Human annotations and adjudications.
- Comparison with baseline/prior release.
- Release decision and approvers.

## 20. Evaluation Result Schema

A machine-readable run summary should follow this shape:

```json
{
  "runId": "eval-2026-10-15-001",
  "suiteVersion": "recommendation-holdout-v3",
  "applicationVersion": "git-sha-or-image-digest",
  "datasetVersion": "dataset-v4",
  "scoringVersion": "score-v2",
  "promptVersion": "prompt-v5",
  "model": {
    "provider": "configured-provider",
    "id": "configured-model",
    "parameters": {"temperature": 0.1}
  },
  "summary": {
    "cases": 200,
    "passed": 198,
    "failed": 2,
    "hardConstraintCompliance": 1.0,
    "postGuardMembershipAccuracy": 1.0,
    "postGuardFactualConsistency": 1.0,
    "fallbackSuccessRate": 1.0,
    "meanExplanationScore": 8.4,
    "ndcgAt5": 0.89,
    "p95LatencyMs": 4200,
    "meanEstimatedCost": 0.0
  },
  "decision": "fail",
  "failedGates": ["unsupported-claim-rate"],
  "createdAt": "ISO-8601 timestamp"
}
```

The sample values illustrate structure only. Actual cost and quality thresholds must come from approved configuration and measured runs.

## 21. Release Scorecard

Use this scorecard for every release candidate.

| Area | Gate | Target | Evidence |
|---|---|---:|---|
| Ingestion | Failed publication changes active data | 0 | Failure-injection test |
| Filtering | Hard-constraint compliance | 100% | Regression and property tests |
| Membership | Unknown returned restaurant IDs after guard | 0 | Adversarial suite |
| Facts | Post-guard factual consistency | 100% | Record comparison |
| Grounding | Unsupported factual claims after validation | 0 | Automated plus human review |
| Fallback | Valid eligible requests served during provider failure | 100% | Failure-injection suite |
| Output | Invalid schema reaches client | 0 | Contract/adversarial suite |
| Relevance | Regression versus approved baseline | None beyond approved margin | Holdout ranking report |
| Explanations | Mean rubric score | Initially at least 8/10 | Blinded human evaluation |
| Accessibility | Critical/serious core-flow defects | 0 | Automated and manual audit |
| Security | Unresolved critical issues | 0 | Security report |
| Reliability | Required failure scenarios pass | 100% | Resilience report |
| Performance | Agreed p95 targets pass | 100% | Production-like load test |
| Cost | Approved per-request and aggregate budgets | Within budget | Cost report |
| Operations | Backup, rollback, dashboards, and alerts exercised | Complete | Operational review |

Any failed non-negotiable gate results in a failed release decision regardless of aggregate score.

## 22. Phase-Wise Evaluation Deliverables

### Phase 0

- Dataset profile.
- Initial synthetic fixture.
- Test and evaluation tooling baseline.
- Agreed metric definitions.

### Phase 1

- Ingestion-quality report.
- Normalization and publication regression suite.
- Version rollback evidence.
- Frozen source snapshot.

### Phase 2

- Filter and score gold cases.
- Property-based invariant suite.
- Deterministic relevance baseline.
- No-match and relaxation evaluation.

### Phase 3

- Versioned prompt suite.
- Adversarial model-output suite.
- Human relevance and explanation rubric.
- First model-versus-baseline report.
- Cost and latency baseline.

### Phase 4

- Browser journey report.
- Accessibility audit.
- Presentation and error-state verification.

### Phase 5

- Production-like load report.
- Resilience and recovery report.
- Security assessment.
- Deployment, rollback, backup, and alert evidence.

### Phase 6

- Complete release scorecard.
- Holdout evaluation report.
- Requirements traceability evidence.
- Canary evaluation and final release decision.

## 23. Minimum Initial Evaluation Suite

Before MVP release, the suite must include at least:

- One standard case for each supported city in the release scope.
- Boundary cases for each hard filter.
- Cases with each optional preference omitted.
- Multi-cuisine and multi-locality cases.
- Missing rating, cost, cuisine, and locality cases.
- Exact-match counts of 0, 1, below requested, exactly requested, and above candidate bounds.
- Every minimum release-blocking case identified in `edge-case.md` that applies to the implemented feature set.
- At least one provider timeout, rate-limit, malformed output, refusal, unknown-ID, duplicate-ID, and unsupported-claim case.
- Prompt injection in both user and dataset text.
- Cache, database, provider, telemetry, and ingestion failure cases.
- Desktop, mobile, keyboard, and screen-reader core flows.
- Production-like common, broad, burst, and sustained-load profiles.

The number of cases should grow based on source-data diversity and defect history. Case count alone is not a quality metric; coverage and assertion strength matter more.

## 24. Ownership and Change Control

Suggested ownership:

- Data engineer: ingestion quality and dataset-version evaluation.
- Backend engineer: filtering, scoring, contracts, guard, and resilience evaluation.
- AI/ML engineer: prompt, model, ranking, grounding, and cost evaluation.
- Frontend engineer: UI flows and automated accessibility checks.
- Product/design: relevance rubric, preference semantics, and manual usability review.
- Security/operations: threat, load, recovery, alert, and deployment evaluation.

Any change to a metric definition, threshold, evaluation case, rubric, or judge must be versioned and reviewed. Do not delete failing cases merely to make a new configuration pass. Retire a case only when the related behavior is intentionally removed or the case is proven invalid, and retain the decision record.

## 25. Definition of Evaluation Readiness

The project is evaluation-ready when:

1. A frozen dataset and synthetic fixture can be loaded reproducibly.
2. Every run captures all required version metadata.
3. Deterministic correctness checks execute without an LLM.
4. Provider calls can be replaced with recorded or fake responses.
5. Raw and post-guard model behavior can be measured separately.
6. Human evaluators have a calibrated rubric and blinded workflow.
7. Performance, cost, security, and resilience suites run in a production-like environment.
8. Reports are machine-readable, comparable with prior runs, and linked to a release decision.

## 26. Definition of Evaluation Success

The evaluation program succeeds when it can demonstrate, with reproducible evidence, that the released system:

- Never violates declared hard constraints.
- Never exposes an unknown restaurant or model-altered fact.
- Provides useful ranking and supported explanations relative to a deterministic baseline.
- Clearly discloses unverifiable preferences and data limitations.
- Continues serving grounded deterministic results during LLM failure.
- Meets approved accessibility, security, reliability, latency, and cost gates.
- Detects regressions before deployment and identifies drift after launch.
