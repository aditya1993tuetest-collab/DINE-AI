# Edge-Case and Corner-Scenario Catalog

## 1. Purpose

This document catalogs exceptional, ambiguous, adversarial, boundary, and failure scenarios for the AI-powered restaurant recommendation system. It is derived from [implementation-plan.md](implementation-plan.md), [architecture.md](architecture.md), and the product requirements in [problemStatement.md](problemStatement.md).

The catalog is intended to drive implementation decisions, acceptance criteria, automated tests, failure-injection exercises, and operational runbooks. Stable case IDs should be referenced from test names and defect reports.

This is a living catalog. A newly discovered production issue must result in a new case or an expansion of an existing case before the issue is considered closed.

## 2. Severity and Test-Layer Legend

### 2.1 Severity

| Severity | Meaning |
|---|---|
| P0 | Can expose secrets, corrupt active data, bypass hard constraints, or return fabricated restaurant facts |
| P1 | Breaks a core recommendation flow, grounding guarantee, fallback path, or release safety control |
| P2 | Produces confusing, incomplete, slow, or inconsistent behavior with a usable recovery path |
| P3 | Minor presentation, diagnostics, or unusual usability issue |

### 2.2 Test Layers

| Code | Layer |
|---|---|
| U | Unit test |
| P | Property-based test |
| I | Integration test |
| C | Contract test |
| E | Browser end-to-end test |
| S | Security or adversarial test |
| F | Failure-injection or resilience test |
| L | Load or performance test |
| M | Manual or exploratory verification |

## 3. Global Behavioral Invariants

These rules take precedence over individual scenario handling:

1. A returned restaurant must belong to the active dataset version used for the request.
2. A returned restaurant must satisfy every hard constraint unless the response explicitly identifies an accepted relaxation.
3. Restaurant facts must come from trusted records, never from generated model text.
4. Missing data must remain missing or be labeled unavailable; it must not be invented.
5. LLM failure must not prevent deterministic recommendations when eligible candidates exist.
6. A dataset publication failure must not modify the active dataset.
7. User input, dataset text, cached content, and LLM output are untrusted.
8. A cache entry must never cross dataset, scoring, prompt, model, currency, or normalized-query boundaries.
9. Every failure response must have a request ID and stable error code without exposing secrets or internal stack traces.
10. Constraint relaxation must never happen silently.

## 4. Dataset Acquisition and Source Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| DATA-001 | Hugging Face is unreachable | Abort the new ingestion with a classified source error; keep the active version unchanged | P1 | I, F |
| DATA-002 | Download times out midway | Remove or abandon incomplete staging state safely; allow a later idempotent retry | P1 | I, F |
| DATA-003 | Authentication is unexpectedly required | Fail with a configuration/source-access error without logging credentials | P1 | I, S |
| DATA-004 | Requested source revision does not exist | Fail before database publication and report the exact safe revision identifier | P1 | I |
| DATA-005 | Source resolves `latest` to new content | Record the resolved immutable revision and content hash; never label it as an older version | P1 | I |
| DATA-006 | Same revision returns different content | Treat the content-hash mismatch as a new or suspicious artifact and block silent overwrite | P1 | I, S |
| DATA-007 | Dataset contains no rows | Fail quality gates; do not activate an empty version | P1 | U, I |
| DATA-008 | Dataset row count drops sharply | Fail or require explicit approval according to the configured quality threshold | P1 | I |
| DATA-009 | Dataset row count grows unexpectedly | Enforce resource bounds, complete validation if possible, and flag the quality deviation | P2 | I, L |
| DATA-010 | Required column is missing | Fail schema validation before normalization or publication | P1 | U, I |
| DATA-011 | Required column is renamed | Fail with an actionable schema-drift report; never guess the mapping | P1 | U, I |
| DATA-012 | Additional unknown columns appear | Ignore or preserve only according to an explicit allowlist; do not expose them automatically | P2 | U, I |
| DATA-013 | Column type changes across revisions | Reject incompatible values and fail quality gates when the error threshold is exceeded | P1 | U, I |
| DATA-014 | Source file has invalid encoding | Reject or quarantine affected rows according to policy and report counts | P2 | U, I |
| DATA-015 | One split is missing or renamed | Fail if the split is required; otherwise record exactly which splits were ingested | P2 | I |
| DATA-016 | Multiple splits contain duplicate records | Apply the documented cross-split deduplication policy and report duplicate counts | P2 | U, I |
| DATA-017 | Downloaded artifact is truncated or corrupt | Detect through parser failure or hash validation and do not stage partial data | P1 | I, F |
| DATA-018 | Dataset license or metadata is absent | Block production activation until the usage decision is documented | P1 | M |
| DATA-019 | Local fixture differs from production schema | Contract test fails; fixture must be updated before ingestion changes merge | P2 | C |
| DATA-020 | Two operators start the same ingestion | Use a revision/content lock or idempotency key so only one publication proceeds | P1 | I, F |

## 5. Normalization, Parsing, and Data-Quality Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| NORM-001 | Restaurant name is null or blank | Reject the row or mark it unusable according to the canonical-model policy | P1 | U |
| NORM-002 | Name differs only by case or whitespace | Normalize for comparison while preserving the source display name | P2 | U, P |
| NORM-003 | Name contains emoji or non-Latin characters | Preserve valid Unicode and generate a stable normalized comparison value | P2 | U |
| NORM-004 | Name contains HTML or script text | Store as text, never execute it, and render escaped | P0 | U, S, E |
| NORM-005 | City has leading, trailing, or repeated whitespace | Canonicalize whitespace and preserve the original display value if needed | P2 | U |
| NORM-006 | City has spelling variants | Apply only approved aliases; do not merge uncertain locations automatically | P2 | U, M |
| NORM-007 | City and locality are swapped | Do not guess unless an explicit deterministic mapping exists; flag the record | P2 | U |
| NORM-008 | City is missing but address contains a city name | Do not extract it as fact unless a tested extraction rule is explicitly adopted | P2 | U |
| NORM-009 | Cuisine field is null | Store an empty or unavailable cuisine set; it cannot satisfy a cuisine constraint | P2 | U, P |
| NORM-010 | Cuisine list uses commas, slashes, semicolons, or mixed delimiters | Parse only recognized delimiter rules and test each form | P2 | U |
| NORM-011 | Cuisine appears more than once | Deduplicate cuisines while preserving a stable display order | P3 | U, P |
| NORM-012 | Cuisine casing or spacing differs | Normalize consistently for matching | P2 | U, P |
| NORM-013 | Cuisine label is a substring of another | Match tokens exactly after normalization, not by unsafe substring | P1 | U, P |
| NORM-014 | Rating is blank, `NEW`, `-`, or `N/A` | Store rating as unavailable; do not coerce it to zero | P1 | U |
| NORM-015 | Rating is negative or above its scale | Reject or null the invalid field and count the quality error | P1 | U, P |
| NORM-016 | Rating uses a decimal comma | Parse only when source locale rules make it unambiguous | P2 | U |
| NORM-017 | Rating scale changes from 5 to 10 | Preserve the declared scale and normalize only through an explicit formula | P1 | U, I |
| NORM-018 | Vote count is negative or nonnumeric | Treat it as unavailable and do not use confidence adjustment | P2 | U |
| NORM-019 | Rating is high with zero votes | Retain source rating but apply the documented confidence behavior | P2 | U |
| NORM-020 | Cost includes currency symbols and grouping separators | Parse using explicit currency and locale rules into integer minor units | P1 | U |
| NORM-021 | Cost is negative | Mark invalid and exclude from budget-constrained matching | P1 | U, P |
| NORM-022 | Cost is zero | Preserve only if zero is a valid source value; otherwise classify as missing/invalid | P2 | U |
| NORM-023 | Cost contains a range | Apply a documented representative-value policy or leave it non-comparable | P2 | U |
| NORM-024 | Cost says `for two`, `per person`, or has no basis | Do not compare unlike bases until normalized; record the basis | P1 | U, I |
| NORM-025 | Currency is missing | Keep display text if useful but exclude from numeric budget filtering | P1 | U, P |
| NORM-026 | Multiple currencies occur | Compare only records with the requested comparable currency; do not perform hidden conversion | P1 | U, I |
| NORM-027 | Cost exceeds integer storage range | Reject safely without overflow or truncated storage | P1 | U, S |
| NORM-028 | Exact duplicate rows occur | Retain one canonical record and report the duplicate count | P2 | U, I |
| NORM-029 | Same source ID has conflicting data | Apply a deterministic conflict policy or reject publication when unresolved | P1 | U, I |
| NORM-030 | No stable source ID exists | Generate a documented fingerprint and handle collision detection | P1 | U, P |
| NORM-031 | Two different restaurants create the same fingerprint | Detect collision and add a stable discriminator; never merge silently | P1 | U, I |
| NORM-032 | Optional attributes contain nested or unexpected types | Retain only schema-allowed values; reject unsafe/unbounded payloads | P2 | U, S |
| NORM-033 | Very long string values | Enforce canonical field lengths and record truncation/rejection policy | P2 | U, S |
| NORM-034 | Null bytes or control characters appear | Normalize or reject safely before database insertion and logs | P1 | U, S |
| NORM-035 | Valid row contains incomplete optional data | Ingest it, preserve unavailable fields, and avoid unsupported claims | P2 | U, I |

## 6. Dataset Versioning, Publication, and Database Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| DB-001 | Migration runs on an empty database | Build the complete schema successfully | P1 | I |
| DB-002 | Migration runs against the prior release | Upgrade without losing active records or availability beyond the plan | P1 | I, F |
| DB-003 | Migration fails halfway | Transactionally roll back or follow the documented forward-recovery path | P0 | I, F |
| DB-004 | Two versions attempt activation concurrently | Serialize activation so exactly one version becomes active | P0 | I, F |
| DB-005 | Active-version transaction loses connection | End in either old-active or new-active state, never zero/multiple ambiguous active versions | P0 | I, F |
| DB-006 | Staging load fails midway | Leave the version non-active and safely resumable or repeatable | P1 | I, F |
| DB-007 | Quality validation fails after loading | Mark the version failed and preserve the prior active version | P1 | I |
| DB-008 | Same source revision is ingested twice | Reuse or reject through idempotency policy without duplicate active data | P1 | I |
| DB-009 | Source key duplicates within one version | Database uniqueness prevents publication | P1 | I |
| DB-010 | Restaurant refers to a missing dataset version | Referential integrity rejects the write | P0 | I |
| DB-011 | No active dataset exists at startup | Readiness fails and recommendation API returns `DATASET_UNAVAILABLE` | P1 | I, F |
| DB-012 | Active dataset is retired accidentally | Constraint or transaction prevents an invalid state | P0 | I |
| DB-013 | Prior version is reactivated | Queries and cache versioning immediately use the restored version | P1 | I, F |
| DB-014 | Old version cleanup overlaps live requests | In-flight requests retain valid data through transaction/snapshot policy | P1 | I, F |
| DB-015 | Database connection pool is exhausted | Fail within a bounded timeout, emit metrics, and avoid thread/request leaks | P1 | F, L |
| DB-016 | Query is canceled or times out | Return a stable service error or safe fallback path; do not return partial results | P1 | I, F |
| DB-017 | Read replica lags dataset activation | Route version-sensitive reads consistently or avoid replica until caught up | P1 | I, F |
| DB-018 | Database clock differs from application clock | Use database/server UTC timestamps and avoid correctness based on local wall-clock ordering | P2 | I |
| DB-019 | Budget profile changes during a request | Resolve one configuration version at request start and use it throughout | P1 | I, F |
| DB-020 | Schema constraint and application validation disagree | Prefer the stricter safe outcome, report the defect, and avoid partial writes | P1 | I |

## 7. Request Validation and Preference-Normalization Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| REQ-001 | Request body is empty | Return `400` or `422` with a stable validation error | P2 | C, I |
| REQ-002 | Body is malformed JSON | Return a safe parse error with request ID; no stack trace | P2 | C, S |
| REQ-003 | Unsupported content type | Return `415` or documented validation response | P2 | C |
| REQ-004 | Unknown fields are included | Reject them or ignore them according to a documented, consistent contract | P2 | C |
| REQ-005 | Location is missing with no configured default | Reject with a field-specific error | P2 | U, C |
| REQ-006 | City is blank or whitespace-only | Treat as missing | P2 | U, C |
| REQ-007 | Location is unsupported | Return `UNSUPPORTED_LOCATION` or an exact no-match, not a guessed city | P2 | I, E |
| REQ-008 | Locality belongs to another city | Reject or produce a no-match; never silently change the city | P1 | U, I |
| REQ-009 | City contains unusual Unicode casing | Normalize consistently with ingestion | P2 | U, P |
| REQ-010 | Cuisine list is empty | Treat cuisine as unspecified rather than requiring no cuisine | P2 | U, C |
| REQ-011 | Cuisine list contains duplicates | Deduplicate before filtering and cache-key creation | P3 | U, P |
| REQ-012 | Cuisine count exceeds maximum | Reject before database or LLM work | P2 | C, S |
| REQ-013 | Unknown cuisine is supplied | Return a validation/no-match outcome; never map it to an unrelated cuisine | P2 | I, E |
| REQ-014 | Multiple cuisines are requested | Apply the documented any-match or all-match semantics and disclose it | P1 | U, I |
| REQ-015 | Minimum rating is exactly zero | Accept if within the source scale and treat it consistently | P3 | U, C |
| REQ-016 | Minimum rating equals the maximum scale | Return only exact qualifying records | P2 | U, I |
| REQ-017 | Minimum rating is below zero or above scale | Reject with a field-specific error | P2 | U, C |
| REQ-018 | Minimum rating is `NaN`, infinity, or a numeric string | Reject non-finite/incorrect types according to the contract | P1 | C, S |
| REQ-019 | Budget minimum exceeds maximum | Reject before querying | P2 | U, C |
| REQ-020 | Budget boundary equals restaurant cost | Include the restaurant according to inclusive boundary rules | P2 | U, P |
| REQ-021 | Named budget tier is unknown | Reject rather than applying a hidden default | P2 | U, C |
| REQ-022 | Requested currency is unsupported | Reject or report no comparable data; never silently convert | P1 | U, C |
| REQ-023 | Tier and explicit range conflict | Reject the ambiguous request or define documented precedence | P1 | C |
| REQ-024 | Result count is zero or negative | Reject with a field-specific error | P2 | U, C |
| REQ-025 | Result count exceeds maximum | Reject or clamp only if the contract explicitly says so; disclose clamping | P2 | C, S |
| REQ-026 | Free-form preference is empty | Treat it as absent | P3 | U |
| REQ-027 | Free-form preference exceeds length limit | Reject before logging, caching, or model invocation | P1 | C, S |
| REQ-028 | Free-form preference contains only control characters | Reject or normalize to absent safely | P2 | U, S |
| REQ-029 | Free text contradicts structured input | Structured fields remain authoritative; note the conflict or ask for correction | P1 | U, I, E |
| REQ-030 | Free text asks to ignore system constraints | Treat it as untrusted preference data and continue enforcing all rules | P0 | S, I |
| REQ-031 | Request has valid optional fields omitted | Broaden search using documented defaults | P2 | U, I |
| REQ-032 | Request uses stale API version or schema | Return a documented compatibility error; do not reinterpret fields silently | P2 | C |
| REQ-033 | Request body is extremely large | Reject at ingress/application limits before expensive parsing | P1 | S, L |
| REQ-034 | Duplicate JSON keys are supplied | Use a parser/policy that rejects ambiguity or applies documented behavior | P1 | C, S |
| REQ-035 | Client disconnects during processing | Cancel avoidable downstream work and record a non-error cancellation outcome | P2 | F, L |

## 8. Filtering and Candidate-Retrieval Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| FILT-001 | No filters except required location | Return bounded, deterministically ordered candidates from that location | P2 | I |
| FILT-002 | Exact city matches multiple normalized spellings | Return all records mapped to the approved canonical city | P2 | U, I |
| FILT-003 | Locality is requested | Require locality match in addition to city | P1 | I, P |
| FILT-004 | Rating is missing under a minimum-rating constraint | Exclude the record | P1 | U, P |
| FILT-005 | Cost is missing under a budget constraint | Exclude the record | P1 | U, P |
| FILT-006 | Currency differs under a budget constraint | Exclude the record unless explicit conversion exists | P1 | U, P |
| FILT-007 | Cuisine is missing under a cuisine constraint | Exclude the record | P1 | U, P |
| FILT-008 | Restaurant has one of several requested cuisines | Apply documented any/all semantics exactly | P1 | U, P |
| FILT-009 | Cuisine is a partial text match only | Do not include it unless alias/token rules define equivalence | P1 | U, P |
| FILT-010 | Restaurant lies exactly at every boundary | Include it when boundaries are documented as inclusive | P2 | U, P |
| FILT-011 | More rows match than the database ceiling | Apply deterministic pre-ordering and a stable bounded selection | P1 | I, P, L |
| FILT-012 | Fewer candidates exist than requested results | Return available candidates without duplicates or fabrication | P1 | I, P |
| FILT-013 | Duplicate source records survive ingestion | Prevent duplicate restaurant IDs in the candidate and result sets | P1 | U, I |
| FILT-014 | Active version changes mid-request | Use the version captured at request start for all filtering and rehydration | P0 | I, F |
| FILT-015 | Metadata endpoint returns a value from an inactive version | Prevent it; metadata and recommendations must use the same active version | P1 | I |
| FILT-016 | Query plan becomes a full scan | Detect through performance tests/metrics and fix indexes before release | P2 | L, M |
| FILT-017 | SQL wildcard characters appear in autocomplete | Escape or parameterize them and retain bounded matching behavior | P1 | I, S |
| FILT-018 | SQL injection syntax appears in fields | Treat it as data through parameterized queries | P0 | S, I |
| FILT-019 | Zero exact matches exist | Return no exact recommendations and compute transparent relaxation counts | P1 | I, E |
| FILT-020 | Broad query consumes excessive memory | Stream/bound database results and score only configured limits | P1 | L, F |

## 9. Deterministic Scoring and Ordering Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| SCORE-001 | All candidates have identical scores | Apply documented stable tie-breakers | P2 | U, P |
| SCORE-002 | Score inputs are missing | Use the documented neutral/zero contribution without division errors | P1 | U, P |
| SCORE-003 | All vote counts are missing | Skip confidence adjustment and use the documented rating behavior | P2 | U |
| SCORE-004 | Dataset mean rating cannot be calculated | Use a documented fallback and emit a data-quality signal | P1 | U, I |
| SCORE-005 | Vote threshold is zero | Avoid division by zero and fail configuration validation | P1 | U, C |
| SCORE-006 | Weights do not sum to one | Normalize explicitly or reject configuration at startup | P1 | U, C |
| SCORE-007 | Weight is negative or non-finite | Reject configuration at startup | P1 | U, C |
| SCORE-008 | Score precision causes apparent ties | Use a stable internal precision and deterministic final tie-breaker | P2 | U, P |
| SCORE-009 | Budget range has zero width | Calculate exact-fit behavior without division by zero | P1 | U, P |
| SCORE-010 | Restaurant is cheaper than requested minimum | Apply the documented budget-fit rule without excluding it unless minimum is hard | P2 | U |
| SCORE-011 | Restaurant exactly equals preferred budget midpoint | Award the documented maximum budget-fit value | P3 | U |
| SCORE-012 | Locality data is missing | Do not award exact-locality score | P2 | U |
| SCORE-013 | Scoring configuration changes | Produce a new configuration version and separate cache/evaluation results | P1 | I |
| SCORE-014 | Same input is processed on different API instances | Produce identical deterministic order | P1 | P, I |
| SCORE-015 | Candidate count is below the LLM bound | Send each candidate once without padding | P1 | U |
| SCORE-016 | Candidate count exceeds the LLM bound | Select the top deterministic candidates using stable ordering | P1 | U, P |
| SCORE-017 | Candidate has an exceptionally high rating but one vote | Confidence adjustment prevents unjustified dominance when vote data exists | P2 | U |
| SCORE-018 | Floating-point implementation changes platform behavior | Use decimal/integer-safe calculations or tolerance plus stable tie-breakers | P1 | P, I |

## 10. No-Match and Relaxation Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| RELAX-001 | City has no restaurants | Report no match; do not propose unrelated cities unless that feature is explicit | P2 | I, E |
| RELAX-002 | Only rating blocks matches | Propose a lower rating threshold with count and exact changed value | P2 | I, E |
| RELAX-003 | Only budget blocks matches | Propose a wider budget with the same currency and explicit range | P2 | I, E |
| RELAX-004 | Only locality blocks matches | Propose city-wide search without changing other constraints | P2 | I, E |
| RELAX-005 | Only cuisine blocks matches | Propose removing or changing cuisine, not a fabricated related cuisine | P2 | I, E |
| RELAX-006 | Several independent relaxations each yield matches | Return each proposal separately with counts | P2 | I |
| RELAX-007 | No single relaxation yields matches | State that no nearby alternative was found; avoid combinatorial explosion | P2 | I, E |
| RELAX-008 | Relaxation count is zero | Omit that proposal | P3 | U, I |
| RELAX-009 | Relaxation count changes after dataset activation | Tie the response to its captured dataset version | P1 | I, F |
| RELAX-010 | User explicitly accepts a relaxation | Create a new normalized query recording the accepted change | P1 | I, E |
| RELAX-011 | UI displays a relaxation as an exact match | Prevent through distinct response types and visual labels | P1 | C, E |
| RELAX-012 | LLM suggests relaxing a constraint | Ignore it; relaxation policy is deterministic application logic | P1 | S, I |
| RELAX-013 | Lowering rating would go below scale | Clamp proposal bounds transparently or omit it | P2 | U |
| RELAX-014 | Widened budget mixes currencies | Do not propose it without explicit conversion support | P1 | U, I |
| RELAX-015 | Missing source value appears only after relaxation | It still cannot satisfy a constraint requiring that value | P1 | P, I |

## 11. Prompt Construction and LLM Input Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| PROMPT-001 | User text contains “ignore previous instructions” | Delimit it as data; hard constraints and system rules remain active | P0 | S |
| PROMPT-002 | Restaurant name contains prompt-like instructions | Treat it as candidate data, never executable instruction | P0 | S |
| PROMPT-003 | Dataset attribute contains JSON-breaking characters | Serialize with a trusted JSON encoder | P1 | U, S |
| PROMPT-004 | Candidate contains newlines or delimiter strings | Preserve safely inside structured serialization | P1 | U, S |
| PROMPT-005 | Free text requests secrets, prompt, or configuration | Do not disclose them; continue or return a safe response | P0 | S |
| PROMPT-006 | Free text requests a restaurant outside candidates | Model instructions prohibit it and response guard rejects it | P0 | S, I |
| PROMPT-007 | Prompt exceeds provider context limit | Reduce candidates deterministically or use fallback; do not truncate schema/instructions | P1 | U, I |
| PROMPT-008 | One candidate has exceptionally long text fields | Exclude nonessential fields and enforce per-field prompt limits | P1 | U |
| PROMPT-009 | No candidates reach prompt builder | Do not call the LLM | P1 | U, I |
| PROMPT-010 | One candidate reaches prompt builder | Ask for at most one result; explanation still requires evidence | P2 | U, I |
| PROMPT-011 | Candidate IDs are visually similar | Preserve exact stable IDs and validate exact equality | P1 | U, I |
| PROMPT-012 | Optional field is unavailable | Encode it as absent/null, not an inferred value | P1 | U |
| PROMPT-013 | Prompt version is missing | Fail configuration/startup or use explicitly defined fallback prompt version | P1 | C |
| PROMPT-014 | Prompt version changes during rolling deployment | Include version in cache key, audit, and request processing | P1 | I, F |
| PROMPT-015 | Candidate order biases model ranking | Evaluate bias and keep deterministic order/version consistent for comparisons | P2 | M, I |
| PROMPT-016 | Soft preference has no supporting field | Require a caveat and prohibit presenting it as verified | P1 | S, I |

## 12. LLM Provider and Model-Output Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| LLM-001 | Provider connection fails | Apply bounded retry policy if transient, then deterministic fallback | P1 | F, I |
| LLM-002 | Provider times out | Cancel/abandon within deadline and return deterministic fallback | P1 | F, I |
| LLM-003 | Provider returns `429` | Respect safe retry guidance within deadline or fall back | P1 | F |
| LLM-004 | Provider returns `500` or `503` | Retry only according to policy, then fall back | P1 | F |
| LLM-005 | Provider rejects credentials | Do not retry repeatedly; fall back, alert, and never expose credential details | P0 | F, S |
| LLM-006 | Provider rejects the configured model | Fall back and raise an actionable configuration alert | P1 | F |
| LLM-007 | Response is empty | One repair/retry only if policy allows, then fallback | P1 | I |
| LLM-008 | Response is truncated JSON | Attempt one bounded structured repair, then fallback | P1 | I |
| LLM-009 | Response contains prose around JSON | Strict parsing rejects it or provider structured mode normalizes it | P1 | I |
| LLM-010 | Response omits required fields | Reject, optionally repair once, then fallback | P1 | I |
| LLM-011 | Response includes an unknown restaurant ID | Reject the invalid response; never return the unknown restaurant | P0 | S, I |
| LLM-012 | Response duplicates a restaurant ID | Reject or deterministically deduplicate only if policy explicitly permits; default to repair/fallback | P1 | I |
| LLM-013 | Response ranks more results than requested | Enforce the result count after validation | P1 | I |
| LLM-014 | Response ranks fewer results than requested | Return only valid unique results if policy permits, otherwise repair/fallback | P2 | I |
| LLM-015 | Response omits a better deterministic candidate | Accept if all returned IDs are eligible; evaluate relevance offline | P2 | M |
| LLM-016 | Response changes restaurant rating/cost/location | Ignore generated facts and rehydrate trusted values | P0 | S, I |
| LLM-017 | Explanation claims unsupported ambience or service | Reject, qualify, or fall back according to evidence-validation policy | P0 | S, I, M |
| LLM-018 | Explanation contradicts structured facts | Reject/repair the response; never show the contradiction as fact | P0 | S, I |
| LLM-019 | Explanation contains unsafe HTML or script | Render as escaped text and enforce output limits | P0 | S, E |
| LLM-020 | Explanation contains a URL not in source data | Remove or reject it unless links are explicitly allowed and verified | P1 | S, I |
| LLM-021 | Explanation is excessively long | Enforce schema and rendering length limits | P2 | U, I, E |
| LLM-022 | Explanation is in an unexpected language | Use configured language behavior or safe fallback; do not corrupt facts | P2 | I, M |
| LLM-023 | Model refuses the ranking task | Fall back deterministically | P1 | I |
| LLM-024 | Model outputs offensive or irrelevant text | Reject via validation/moderation policy and fall back | P1 | S, I |
| LLM-025 | Model returns a candidate ID with altered casing | Require exact ID match; do not fuzzy-match identities | P1 | I |
| LLM-026 | Provider response arrives after request timeout | Discard it safely and avoid double audit/cache writes | P1 | F, I |
| LLM-027 | Client disconnects while model call is running | Cancel where supported and do not cache incomplete work | P2 | F |
| LLM-028 | Circuit breaker opens | Skip model calls and return fallback immediately | P1 | F |
| LLM-029 | Circuit breaker half-open probe fails | Reopen without affecting deterministic service | P1 | F |
| LLM-030 | Different provider model is deployed accidentally | Model/version telemetry and release checks detect the mismatch | P1 | C, F |
| LLM-031 | Token usage metadata is missing | Serve validated output but flag cost telemetry as incomplete | P2 | I |
| LLM-032 | Repair response introduces new invalid content | Do not attempt unbounded repairs; fall back after the single allowed attempt | P1 | I |
| LLM-033 | Structured-output feature is unavailable | Adapter uses documented strict parser or refuses startup; grounding rules remain unchanged | P1 | C, I |
| LLM-034 | Model output order is nondeterministic | Accept grounded variance within evaluation thresholds; cache/version it consistently | P2 | M |
| LLM-035 | Provider safety filter blocks benign content | Record categorized failure and use deterministic fallback | P2 | I |

## 13. API Transport and HTTP Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| API-001 | Request ID header is absent | Generate a new valid request ID | P3 | C |
| API-002 | Client supplies a malformed request ID | Replace or safely normalize it; prevent log injection | P1 | S, C |
| API-003 | Client supplies an extremely long header | Reject at ingress limits | P1 | S, L |
| API-004 | Unsupported HTTP method is used | Return `405` with correct allowed methods | P3 | C |
| API-005 | Browser sends a CORS preflight | Permit only configured origins, methods, and headers | P1 | S, E |
| API-006 | Untrusted origin calls the API | CORS blocks browser access; backend security does not rely on CORS alone | P1 | S |
| API-007 | Reverse proxy sends spoofed forwarding headers | Trust them only from configured proxies | P1 | S |
| API-008 | Response serialization encounters invalid text | Fail safely with request ID, never return partial malformed JSON | P1 | I |
| API-009 | Internal exception occurs | Return stable `INTERNAL_ERROR`, redact detail, and log correlated diagnostics | P1 | I, S |
| API-010 | Metadata query is empty | Return a bounded popular/all list or validation outcome according to contract | P3 | C, I |
| API-011 | Metadata query returns too many values | Enforce pagination/limit and deterministic order | P2 | I, L |
| API-012 | Readiness is checked during DB outage | Report not ready with bounded dependency timeout | P1 | F |
| API-013 | Liveness is checked during dependency outage | Report live while process is healthy; do not call dependencies | P1 | F |
| API-014 | LLM is down but DB is healthy | Readiness remains healthy/degraded because fallback is available | P1 | F |
| API-015 | Response compression is abused | Configure safe proxy/server limits against compression-related resource attacks | P1 | S |
| API-016 | Client retries the same read request | Return a valid equivalent response; avoid duplicate harmful side effects | P2 | I |
| API-017 | API instance shuts down during a request | Stop new traffic and allow bounded in-flight completion or safe retry | P1 | F |
| API-018 | Error payload accidentally contains provider body | Redaction tests prevent third-party/internal details reaching clients | P0 | S, C |

## 14. Cache Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| CACHE-001 | Redis is unavailable | Treat as cache miss and continue without cache | P1 | F, I |
| CACHE-002 | Redis times out | Respect a short deadline and continue | P1 | F |
| CACHE-003 | Cached value is malformed | Ignore/delete it safely and recompute | P1 | I, F |
| CACHE-004 | Cached response contains an unknown restaurant ID | Reject through the same response validation or trusted cache schema/version | P0 | S, I |
| CACHE-005 | Dataset version changes | Old entry is bypassed because version is part of the key | P0 | I |
| CACHE-006 | Scoring weights change | Old entry is bypassed through scoring configuration version | P1 | I |
| CACHE-007 | Prompt or model changes | Old LLM result is bypassed through prompt/model version | P1 | I |
| CACHE-008 | Currency differs | Cache keys remain distinct | P1 | U, P |
| CACHE-009 | Equivalent normalized requests differ in formatting | Resolve to the same canonical key | P2 | U, P |
| CACHE-010 | Different free-form preferences hash-collide | Use a cryptographically strong hash and include canonical structured context | P1 | U, S |
| CACHE-011 | Free-form text appears in visible key/logs | Prevent it; key contains only a hash | P1 | S, I |
| CACHE-012 | Entry expires during read | Treat as miss without request failure | P3 | I |
| CACHE-013 | Many identical misses arrive together | Use bounded request coalescing/lock where valuable; avoid a provider stampede | P1 | F, L |
| CACHE-014 | Cache write fails after valid response | Return the response and record cache failure | P2 | F |
| CACHE-015 | Fallback response is cached too long | Use policy-specific short TTL or avoid caching transient-provider fallback | P2 | I |
| CACHE-016 | Negative/no-match response is cached across activation | Versioned key prevents stale no-match use | P1 | I |
| CACHE-017 | Cache memory is full and evicts entries | Service continues with lower hit rate and emits metrics | P2 | F, L |
| CACHE-018 | Two instances serialize canonical keys differently | Shared contract tests enforce identical canonicalization | P1 | C, P |

## 15. Web UI and Presentation Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| UI-001 | JavaScript is slow to load | Show a stable shell/loading state without layout corruption | P3 | E, L |
| UI-002 | API request is slow | Show progress and allow safe cancellation/editing | P2 | E, F |
| UI-003 | User submits twice rapidly | Prevent duplicate UI actions or handle both responses without state corruption | P2 | E |
| UI-004 | Older response arrives after a newer search | Ignore the stale response using request identity/cancellation | P1 | E, F |
| UI-005 | User edits inputs while request is running | Preserve edits and prevent old results from being attributed to new inputs | P1 | E |
| UI-006 | Browser navigates back after results | Restore or deliberately reset state consistently | P3 | E |
| UI-007 | Metadata request fails | Keep manual input or show a recoverable field error without losing other values | P2 | E |
| UI-008 | Selected metadata option becomes stale after activation | Server validation remains authoritative and UI shows the resulting message | P2 | E, I |
| UI-009 | Restaurant name is extremely long | Wrap/truncate visually without losing accessible full text | P3 | E |
| UI-010 | Cuisine list is long | Present a bounded, accessible layout with expansion if needed | P3 | E |
| UI-011 | Rating is unavailable | Show `Not rated` or equivalent, never `0` | P1 | E |
| UI-012 | Cost is unavailable | Show `Cost unavailable`, never a fabricated amount | P1 | E |
| UI-013 | Currency formatting locale differs | Format with currency code and locale safely without changing stored value | P2 | U, E |
| UI-014 | Explanation contains markdown syntax | Render as plain text or sanitized supported markup according to policy | P1 | S, E |
| UI-015 | Explanation contains right-to-left text | Preserve readable layout and avoid spoofed control-character effects | P2 | S, E |
| UI-016 | No matches are found | Show no-match state and separate relaxation options | P1 | E |
| UI-017 | Response uses deterministic fallback | Show useful results and a concise non-alarming limitation indicator | P2 | E |
| UI-018 | Server validation differs from client validation | Display server error next to the correct field and preserve inputs | P2 | E |
| UI-019 | Network disconnects after submission | Show retry option and preserve preferences | P2 | E, F |
| UI-020 | Result count is lower than requested | Display available results without blank placeholders | P3 | E |
| UI-021 | Duplicate result ID appears due to defect | UI keys remain stable, but contract test should block the response upstream | P1 | C, E |
| UI-022 | Dataset limitation disclosure is omitted at small viewport | Keep it accessible and available across supported viewports | P2 | E |
| UI-023 | User refreshes results URL | Handle non-persisted state predictably without exposing preferences in unsafe URLs | P2 | E, S |
| UI-024 | API returns an unknown error code | Show a generic request-ID-based recovery message | P2 | E |
| UI-025 | Client clock is wrong | Do not use client time for dataset correctness or request ordering | P3 | E |

## 16. Accessibility Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| A11Y-001 | User operates with keyboard only | All controls, suggestions, submission, errors, and results are reachable and operable | P1 | E, M |
| A11Y-002 | Autocomplete suggestions open | Focus and ARIA state follow an accessible combobox pattern | P1 | E, M |
| A11Y-003 | Validation fails | Focus moves to or announces the error summary and fields are linked to errors | P1 | E, M |
| A11Y-004 | Results arrive asynchronously | A restrained live region announces completion without reading the entire page | P2 | E, M |
| A11Y-005 | Loading takes several seconds | Loading status is available to screen readers and not conveyed only visually | P2 | E, M |
| A11Y-006 | Rating is shown with stars | Numeric accessible text includes value and scale | P1 | E |
| A11Y-007 | Match quality uses color | Equivalent text or icon labeling communicates the state | P1 | E |
| A11Y-008 | Page is zoomed to 200-400% | Controls and results reflow without loss of function | P2 | E, M |
| A11Y-009 | Reduced-motion preference is enabled | Nonessential animation is reduced or removed | P3 | E |
| A11Y-010 | High-contrast mode is used | Controls, focus, and statuses remain perceivable | P2 | M |
| A11Y-011 | Error message uses technical language | Present actionable plain language while retaining request ID | P2 | E, M |
| A11Y-012 | Result ranks are visually arranged in cards | Semantic ordering matches visual ordering | P1 | E, M |

## 17. Security and Abuse Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| SEC-001 | SQL injection payload in any structured field | Parameterized queries treat it as data | P0 | S |
| SEC-002 | Stored XSS in dataset field | Escape on output; script never executes | P0 | S, E |
| SEC-003 | Reflected XSS in validation message | Escape user values and avoid echoing unsafe content | P0 | S, E |
| SEC-004 | Prompt injection in free text | Model cannot change eligibility, tool access, or response validation | P0 | S |
| SEC-005 | Prompt injection in dataset text | Candidate data remains untrusted and closed-list validation holds | P0 | S |
| SEC-006 | Path traversal in ingestion/config input | Resolve only allowed dataset/config locations | P0 | S |
| SEC-007 | SSRF-like URL appears in source or user text | Never fetch arbitrary URLs during recommendation | P0 | S |
| SEC-008 | LLM API key is accidentally included in client bundle | Build/release scan fails | P0 | S, C |
| SEC-009 | Secret appears in logs or traces | Redaction test fails the release; rotate any exposed credential | P0 | S |
| SEC-010 | Raw prompt or free-form preference appears in telemetry | Omit by default and verify through telemetry tests | P1 | S, I |
| SEC-011 | Attacker floods expensive recommendation endpoint | Rate limit before costly LLM work | P1 | S, L |
| SEC-012 | Attacker rotates payloads to defeat result cache | Rate limits and request-cost controls remain effective | P1 | S, L |
| SEC-013 | Oversized decompressed request body | Edge/application limits reject it before excessive allocation | P0 | S, L |
| SEC-014 | Unicode confusables spoof a restaurant or city | IDs remain authoritative; display text never determines identity | P1 | S, U |
| SEC-015 | Carriage returns are injected into logs | Structured logging encodes values and prevents log forging | P1 | S |
| SEC-016 | Error returns a stack trace | Production handler returns only stable safe fields | P0 | S |
| SEC-017 | API database role attempts writes | Least-privilege permissions deny unauthorized mutation | P0 | S, I |
| SEC-018 | Ingestion role attempts to change secrets/config | Platform permissions deny it | P0 | S |
| SEC-019 | Dependency contains a critical known vulnerability | CI/release gate blocks or requires documented risk acceptance | P1 | S |
| SEC-020 | Container runs as root unnecessarily | Release policy/build test rejects the image | P1 | S |
| SEC-021 | Untrusted origin attempts credentialed CORS | Origin policy denies it | P1 | S |
| SEC-022 | Model response contains data-exfiltration instructions | Treat as text, reject unsafe content, and provide no tools or secrets | P0 | S |
| SEC-023 | Repeated unknown IDs probe internal data | Return generic validation/fallback behavior without exposing candidate internals | P1 | S |
| SEC-024 | Rate-limit store fails open | Apply documented local/bounded fallback controls and alert | P1 | F, S |
| SEC-025 | Rate-limit identity trusts spoofable headers | Use trusted proxy-derived client identity only | P1 | S |

## 18. Reliability, Concurrency, and Resource Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| REL-001 | API process restarts during traffic | Load balancer drains/retries safely; stateless requests recover | P1 | F |
| REL-002 | Deployment terminates model calls mid-flight | Graceful shutdown allows bounded completion or clients receive retryable failure | P1 | F |
| REL-003 | PostgreSQL is unavailable | Readiness fails and API returns bounded service errors; no hanging requests | P1 | F |
| REL-004 | Redis is unavailable | Recommendations continue without cache/shared limit optimization | P1 | F |
| REL-005 | LLM is unavailable | Deterministic recommendations continue | P1 | F |
| REL-006 | All external dependencies are unavailable | Service fails quickly with safe errors; liveness reflects only process health | P1 | F |
| REL-007 | Sudden traffic spike occurs | Rate limits and autoscaling protect dependencies; latency/errors are observable | P1 | L, F |
| REL-008 | Broad queries coincide with ingestion | Online queries retain acceptable latency and consistent active-version reads | P1 | L, F |
| REL-009 | Many clients submit identical requests | Cache/coalescing prevents unnecessary provider amplification | P2 | L, F |
| REL-010 | Many unique expensive requests arrive | Rate limits and candidate/token ceilings bound cost | P1 | L |
| REL-011 | Memory pressure occurs during ingestion | Stream/chunk processing and fail safely without affecting active service | P1 | L, F |
| REL-012 | Disk fills during database or job operation | Alerts fire; transaction fails safely; active data remains consistent | P0 | F |
| REL-013 | System clock jumps backward/forward | Use monotonic timers for duration/deadline logic | P1 | U, F |
| REL-014 | DNS temporarily fails for provider | Retry within policy, then fallback | P1 | F |
| REL-015 | TLS certificate validation fails | Do not bypass validation; fallback and alert | P0 | F, S |
| REL-016 | Response validation consumes excessive CPU | Bound output size before parsing and enforce time/resource limits | P1 | S, L |
| REL-017 | Retry storm follows provider recovery | Jitter and circuit-breaker probing prevent synchronized retries | P1 | F, L |
| REL-018 | Audit write fails after valid recommendation | Return recommendation if audit is noncritical, emit durable alert/metric | P2 | F |
| REL-019 | Request cancellation is not supported by provider SDK | Stop awaiting after deadline and prevent late writes | P1 | F |
| REL-020 | Partial network partition affects one API instance | Health checks remove unhealthy instance without corrupting shared state | P1 | F |

## 19. Observability and Audit Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| OBS-001 | Request has no request ID | Generate and propagate one through logs, traces, and response | P2 | I |
| OBS-002 | Provider request ID is unavailable | Keep internal correlation and mark provider ID absent | P3 | I |
| OBS-003 | Metrics backend is unavailable | User request continues; telemetry failure is bounded | P2 | F |
| OBS-004 | Trace exporter is slow | Export asynchronously with bounded buffers and no request-path blockage | P2 | F, L |
| OBS-005 | Log sink is unavailable | Apply bounded buffering/drop policy without exhausting memory | P1 | F, L |
| OBS-006 | High-cardinality text reaches metric labels | Prevent it through an allowlisted metric schema | P1 | S, I |
| OBS-007 | Raw user text appears in logs | Redaction/absence test fails | P1 | S |
| OBS-008 | Dataset/prompt/scoring version is absent from audit | Mark audit incomplete and fail release checks for applicable flows | P1 | I |
| OBS-009 | Token usage is absent | Preserve request success and record `unknown`, not zero | P2 | I |
| OBS-010 | Estimated cost calculation uses stale price configuration | Version pricing metadata and distinguish estimate from invoice | P2 | U, I |
| OBS-011 | Health alert fires during planned deployment | Maintenance/deployment-aware alerting avoids false escalation | P3 | F, M |
| OBS-012 | Grounding validation failures increase suddenly | Alert on rate change and retain safe categorized examples without sensitive text | P1 | F, M |
| OBS-013 | No-match rate changes after dataset activation | Dashboard breaks down by dataset version | P2 | I, M |
| OBS-014 | Logs contain different timestamps/time zones | Emit UTC with standard format | P3 | U, I |
| OBS-015 | Request succeeds through fallback | Record success mode separately from full LLM success | P1 | I |

## 20. Deployment, Configuration, and Recovery Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| DEP-001 | Required environment variable is missing | Fail startup with the setting name but no secret values | P1 | C |
| DEP-002 | Numeric configuration is malformed | Fail startup instead of silently using an unsafe default | P1 | C |
| DEP-003 | Candidate limit is below result limit | Reject configuration at startup | P1 | C |
| DEP-004 | Timeout is zero, negative, or excessive | Reject configuration outside safe bounds | P1 | C |
| DEP-005 | Production starts with development fake model | Environment validation blocks startup/release | P0 | C, S |
| DEP-006 | Two application versions run during rolling deployment | Database and API contracts remain backward compatible | P1 | I, F |
| DEP-007 | New app starts before migration completes | Readiness remains false or deployment ordering prevents traffic | P1 | F |
| DEP-008 | Migration is newer than running app supports | Compatibility guard blocks unsafe startup | P1 | C, F |
| DEP-009 | Canary has a new prompt/model version | Metrics distinguish it from stable instances | P1 | I, M |
| DEP-010 | Rollback uses an older app with a newer schema | Migration strategy preserves backward compatibility or runbook handles it | P0 | I, F |
| DEP-011 | Container image architecture is incompatible | CI build/run verification blocks promotion | P2 | C |
| DEP-012 | Static client points to the wrong API environment | Build-time/runtime environment validation detects it | P1 | C, E |
| DEP-013 | CORS allows a staging origin in production | Security configuration test blocks release | P1 | S |
| DEP-014 | Secret rotation occurs during runtime | New connections use the rotated secret without exposing it; recovery is documented | P1 | F, S |
| DEP-015 | Database backup is corrupt | Restore drill detects it and escalation uses a prior valid backup | P0 | F, M |
| DEP-016 | Point-in-time recovery omits latest dataset activation | Restore to consistent state and explicitly select a valid active version | P1 | F |
| DEP-017 | Retired dataset is deleted before audit retention ends | Retention policy prevents loss of required traceability | P1 | I, M |
| DEP-018 | Rollback does not clear incompatible cache entries | Versioned keys or namespace rotation prevents reuse | P1 | F, I |
| DEP-019 | Provider quota is exhausted after deployment | Alert and serve deterministic fallback | P1 | F |
| DEP-020 | Deployment artifact differs from staging-tested artifact | Immutable digest promotion check blocks release | P0 | C |

## 21. Offline Evaluation and Model-Quality Cases

| ID | Scenario | Expected behavior | Severity | Tests |
|---|---|---|---|---|
| EVAL-001 | Evaluation fixture references retired/missing IDs | Pin it to a dataset version or migrate it explicitly | P1 | C |
| EVAL-002 | Prompt change improves fluency but adds unsupported claims | Fail grounding threshold despite subjective fluency gain | P0 | M, S |
| EVAL-003 | Model change reduces relevance for one city/cuisine | Segment metrics and block release when critical cohorts regress | P1 | M |
| EVAL-004 | Deterministic baseline outperforms LLM | Keep or prefer deterministic ordering until LLM value is demonstrated | P2 | M |
| EVAL-005 | Human evaluators disagree | Use a defined rubric, adjudication, and agreement measurement | P2 | M |
| EVAL-006 | Evaluation set overrepresents popular locations | Add balanced cohorts before generalizing results | P2 | M |
| EVAL-007 | Only happy-path preferences are evaluated | Add missing, conflicting, unsupported, and adversarial profiles | P1 | M, S |
| EVAL-008 | Results vary between repeated runs | Measure variance and ensure all variants preserve invariants | P2 | M, P |
| EVAL-009 | Cost/latency improves by reducing candidates | Revalidate relevance before adopting the lower bound | P2 | L, M |
| EVAL-010 | Provider silently updates model behavior | Monitor version/fingerprint where available and run scheduled regression checks | P1 | M |
| EVAL-011 | Explanations mention all facts but do not address preference | Fail relevance/evidence-coverage rubric | P2 | M |
| EVAL-012 | Caveats overwhelm useful recommendations | Tune prompt/UI while keeping unverifiable claims clearly disclosed | P3 | M, E |

## 22. Business-Logic Ambiguities Requiring Explicit Decisions

These are not safe to resolve implicitly in code. Each requires a documented product or data decision before the related feature is considered complete.

| ID | Ambiguity | Required decision |
|---|---|---|
| DEC-001 | Multiple requested cuisines | Whether a restaurant must match any cuisine or all cuisines |
| DEC-002 | Budget meaning | Per-person, for-two, order total, or dataset-native definition |
| DEC-003 | Named budget tiers | Currency-specific numeric boundaries and versioning |
| DEC-004 | Budget minimum | Whether it is a hard lower bound or merely a preference |
| DEC-005 | Location match | Exact city/locality rules and approved aliases |
| DEC-006 | Unrated restaurants | Whether they are eligible when no minimum rating is supplied |
| DEC-007 | Missing cost | Whether it may appear when no budget is supplied |
| DEC-008 | Rating confidence | Whether vote count affects order and the chosen formula/threshold |
| DEC-009 | Soft preference interpretation | Which concepts are extractable and what evidence supports them |
| DEC-010 | LLM short result | Whether fewer valid model-ranked results are accepted or trigger fallback |
| DEC-011 | Invalid LLM explanation | Reject one item, repair the response, or fall back for the whole request |
| DEC-012 | Relaxation execution | Whether user confirmation is always required |
| DEC-013 | Related cuisine suggestions | Whether an approved cuisine taxonomy exists |
| DEC-014 | Cache policy for fallback | Whether and how long degraded responses are cached |
| DEC-015 | Raw-query retention | Whether user consent/legal basis permits storing free-form text for evaluation |
| DEC-016 | Duplicate restaurant branches | Whether branches share identity or remain separate location-specific records |
| DEC-017 | Source freshness disclosure | Exact UI wording and location |
| DEC-018 | Default result count | Default value and maximum supported value |
| DEC-019 | Supported languages | Input and explanation languages in the MVP |
| DEC-020 | Unknown API fields | Reject for strictness or ignore for forward compatibility |

## 23. Minimum Release-Blocking Scenario Suite

The following cases must be automated and passing before production release:

- `DATA-001`, `DATA-010`, `DATA-017`, and `DATA-020`.
- `NORM-004`, `NORM-015`, `NORM-020`, `NORM-025`, and `NORM-029`.
- `DB-003`, `DB-004`, `DB-005`, `DB-011`, and `DB-013`.
- `REQ-008`, `REQ-018`, `REQ-023`, `REQ-029`, and `REQ-030`.
- `FILT-004` through `FILT-010`, `FILT-014`, and `FILT-018`.
- `SCORE-001`, `SCORE-005` through `SCORE-009`, and `SCORE-014`.
- `RELAX-006`, `RELAX-010`, `RELAX-011`, and `RELAX-012`.
- `PROMPT-001` through `PROMPT-007` and `PROMPT-016`.
- `LLM-001` through `LLM-013`, `LLM-016` through `LLM-019`, and `LLM-026` through `LLM-032`.
- `CACHE-001`, `CACHE-004` through `CACHE-010`, and `CACHE-013`.
- `UI-004`, `UI-005`, `UI-011`, `UI-012`, `UI-014`, and `UI-016` through `UI-019`.
- `A11Y-001` through `A11Y-008` and `A11Y-012`.
- `SEC-001` through `SEC-018` and `SEC-022` through `SEC-025`.
- `REL-001` through `REL-017` and `REL-020`.
- `DEP-001` through `DEP-010`, `DEP-014` through `DEP-016`, and `DEP-020`.

## 24. Test Data Matrix

The maintained fixture should contain enough synthetic or approved source-derived records to exercise these dimensions:

| Dimension | Required examples |
|---|---|
| Location | Multiple cities, multiple localities in one city, missing locality, alias spelling |
| Cuisine | Single cuisine, multiple cuisines, duplicate cuisine, missing cuisine, substring-confusable labels |
| Rating | Minimum, maximum, boundary, missing, malformed, high rating with low votes |
| Cost | Below/at/above budget, missing, malformed, range, multiple currencies, different cost basis |
| Identity | Stable ID, duplicate row, conflicting duplicate, branch with same name |
| Text safety | HTML, script-like text, prompt-injection text, Unicode, right-to-left controls, long values |
| Optional attributes | Supported true/false, missing, and unexpected raw value |
| Recommendation results | Zero, one, fewer than requested, exactly requested, and more than candidate ceiling |

The fixture must remain small enough for fast tests and deterministic enough that expected candidate IDs and order can be asserted directly.

## 25. Scenario-to-Test Naming Convention

Use the stable ID in every automated test name or display name. Examples:

```text
test_NORM_015_rejects_rating_above_scale
test_FILT_005_missing_cost_fails_budget_constraint
test_LLM_011_unknown_restaurant_triggers_fallback
test_CACHE_005_dataset_version_separates_entries
test_UI_004_ignores_stale_response
```

When one test covers several cases, list all IDs in test metadata. When a production defect reveals an uncovered variation, add a new stable case rather than changing the meaning of an existing ID.

## 26. Completion Criteria for Edge-Case Coverage

Edge-case coverage is acceptable for the MVP when:

1. Every P0 and P1 case applicable to the implemented feature set has an automated test or documented failure-injection exercise.
2. Every release-blocking case passes in CI, staging, or the designated security/resilience pipeline.
3. Every unresolved business ambiguity has a recorded decision or is excluded from the released feature set.
4. Hard-constraint violations, unknown restaurant IDs, and model-modified facts reaching users remain at zero.
5. Ingestion, deployment, provider outage, cache outage, and database recovery runbooks have been exercised.
6. P2 and P3 cases are prioritized in the delivery backlog with explicit ownership.
7. Production incidents and evaluation regressions feed back into this catalog and the automated test suite.
