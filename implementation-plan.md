# Phase-Wise Implementation Plan

## 1. Purpose

This plan converts the requirements in [problemStatement.md](problemStatement.md) and the design in [architecture.md](architecture.md) into an ordered implementation roadmap for the AI-powered restaurant recommendation system.

The plan is organized around testable increments. Each phase has prerequisites, work packages, deliverables, validation activities, and an exit gate. A phase is complete only when its exit criteria are met; completing code without tests, documentation, or operational checks does not complete a phase.

## 2. Delivery Principles

The implementation must follow these rules throughout all phases:

1. **Build deterministic value first.** The product must filter and rank useful restaurant candidates before an LLM is introduced.
2. **Keep facts outside the LLM.** Restaurant name, location, cuisine, rating, and cost are always rehydrated from trusted application data.
3. **Version important behavior.** Dataset revisions, schema, budget profiles, scoring configuration, prompts, and model identifiers must be traceable.
4. **Test at module boundaries.** Dataset adapters, repositories, scoring, prompting, provider integration, and response validation must be independently testable.
5. **Prefer reversible changes.** Dataset activation, database migrations, deployments, and prompt releases require a rollback path.
6. **Treat all external text as untrusted.** User text, dataset content, and model output require validation and safe rendering.
7. **Do not silently relax constraints.** Any relaxation must be explicit in the response.
8. **Keep the system usable without the LLM.** Provider failure must lead to deterministic fallback, not total request failure.

## 3. Assumed Delivery Model

The plan assumes:

- A modular monolith backend using Python, FastAPI, Pydantic, and PostgreSQL.
- A React and TypeScript web application.
- Redis for shared caching and rate limiting when production readiness requires it.
- A provider-neutral LLM adapter.
- Docker-based local development and deployment artifacts.
- One source repository containing the API, web application, database migrations, documentation, and tests.

These are the reference choices from the architecture. If a choice changes, record the decision before implementation and preserve the same component boundaries.

## 4. Phase Overview

| Phase | Outcome | Depends on | Relative effort |
|---|---|---|---|
| Phase 0 | Agreed foundations and runnable repository skeleton | None | Small |
| Phase 1 | Versioned, validated restaurant data in PostgreSQL | Phase 0 | Medium |
| Phase 2 | Useful deterministic recommendation API | Phase 1 | Large |
| Phase 3 | Grounded LLM ranking with reliable fallback | Phase 2 | Large |
| Phase 4 | Accessible end-user web experience | Stable Phase 2 API; Phase 3 for final integration | Medium |
| Phase 5 | Production-ready security, reliability, and operations | Phases 1-4 | Large |
| Phase 6 | Release validation, launch, and post-launch hardening | Phase 5 | Medium |

Phase 4 frontend scaffolding can begin while Phase 3 is in progress once the API contract is stable. Production release still requires both phases to pass their exit gates.

## 5. Cross-Phase Workstreams

Some work is continuous rather than confined to a single phase.

### 5.1 Quality and Testing

- Add tests with each behavior, not as a final cleanup task.
- Maintain small, deterministic fixtures independent of the full source dataset.
- Add regression cases whenever a defect is found.
- Keep test categories separate: unit, integration, contract, end-to-end, evaluation, performance, and security.
- Publish coverage and test results in continuous integration.

### 5.2 Documentation and Decisions

- Record material design changes as architecture decision records under `docs/decisions/`.
- Keep environment setup and common commands current.
- Document every configuration value and default.
- Version prompt templates and evaluation rubrics.
- Maintain API documentation from the OpenAPI contract.

### 5.3 Security and Privacy

- Keep secrets out of the repository from the first commit.
- Avoid logging raw free-form preferences by default.
- Review new external dependencies and outbound integrations.
- Add threat cases alongside feature acceptance tests.
- Preserve least-privilege access between runtime components.

### 5.4 Observability

- Introduce request and job IDs early.
- Use structured logs from the first executable service.
- Add metrics when each behavior is introduced.
- Never defer all telemetry work until deployment.

## 6. Phase 0: Foundations and Technical Discovery

### 6.1 Objective

Remove implementation ambiguity, inspect the actual dataset, establish engineering standards, and produce a runnable repository skeleton.

### 6.2 Prerequisites

- Access to the source repository.
- Access to the Hugging Face dataset or a representative exported sample.
- Agreement on supported deployment environments.
- A decision on the first LLM provider may remain open, but the configuration and adapter boundary must be agreed.

### 6.3 Work Package 0.1: Dataset Discovery

Tasks:

- Download or inspect the exact Hugging Face dataset revision.
- Record available splits, row counts, column names, data types, and representative values.
- Measure missing values, malformed ratings and costs, duplicate rates, location coverage, cuisine coverage, and currency variation.
- Determine whether the dataset supplies stable restaurant identifiers.
- Determine the actual rating scale and meaning of cost fields.
- Identify which optional attributes can support claims such as delivery, booking, restaurant type, or dining suitability.
- Create a sanitized, small fixture that covers valid, missing, duplicate, and malformed records.
- Write `docs/data-profile.md` containing findings and decisions.

Deliverables:

- Dataset profile and source revision.
- Initial source-to-canonical field mapping.
- Small version-controlled test fixture.
- List of unsupported assumptions from the problem statement.

Validation:

- Every canonical field maps to a real source field or is marked as derived.
- Rating scale, cost semantics, and currency behavior are documented.
- The fixture contains no secret or inappropriate personal data.

### 6.4 Work Package 0.2: Architecture Decision Confirmation

Tasks:

- Confirm the modular-monolith approach.
- Confirm Python/FastAPI, React/TypeScript, PostgreSQL, and the initial cache strategy.
- Decide whether Redis is required locally from the start or introduced in Phase 5.
- Confirm package management and supported language/runtime versions.
- Define environment names and configuration conventions.
- Record the initial architecture decisions under `docs/decisions/`.
- Define the provider-neutral LLM protocol without selecting provider-specific behavior.

Deliverables:

- Accepted ADRs for stack, module boundaries, data versioning, and LLM grounding.
- Runtime and tool version policy.

### 6.5 Work Package 0.3: Repository Bootstrap

Tasks:

- Create the repository structure defined in the architecture.
- Initialize backend and frontend dependency manifests.
- Add formatting, linting, type-checking, and test configuration.
- Add an initial FastAPI service with `/health/live`.
- Add an initial React application with a basic route and API client boundary.
- Add Dockerfiles and a local Compose configuration for the API, web app, and PostgreSQL.
- Add `.env.example` containing names but no secret values.
- Add pre-commit or equivalent local quality checks.
- Add a README with setup, run, test, and migration commands.

Recommended checks:

- Backend formatting and linting.
- Backend static type checking.
- Frontend formatting, linting, and TypeScript checking.
- Unit test commands for both applications.
- Container build verification.

### 6.6 Work Package 0.4: Continuous Integration Baseline

Tasks:

- Configure CI for lint, type-check, tests, and builds.
- Cache dependencies without caching secret-bearing files.
- Add dependency and secret scanning.
- Upload test reports on failures.
- Require checks to pass before merging.

### 6.7 Phase 0 Exit Criteria

- The actual dataset has been inspected and documented.
- The repository starts locally with documented commands.
- The API liveness endpoint and web shell run successfully.
- Formatting, linting, type-checking, tests, and builds execute in CI.
- No credentials are committed.
- Architectural decisions that affect Phase 1 are resolved.

## 7. Phase 1: Data Foundation

### 7.1 Objective

Build a repeatable ingestion pipeline that transforms a pinned source revision into a validated, immutable, and atomically activated PostgreSQL dataset version.

This phase satisfies the foundation of FR-01, FR-02, FR-10, and FR-12.

### 7.2 Work Package 1.1: Canonical Domain Model

Tasks:

- Define domain types for restaurant, location, cuisine, monetary cost, rating, and dataset version.
- Separate source display fields from normalized comparison fields.
- Define nullability based on the completed data profile.
- Use integer minor units and a currency code for comparable cost values.
- Define a stable `source_key`; derive a fingerprint only if the source lacks a durable ID.
- Specify normalization rules for Unicode, whitespace, case, separators, and aliases.
- Define the policy for invalid ratings, unknown currencies, missing cost, and unrated restaurants.
- Define the duplicate resolution policy and preserve audit counts.

Implementation notes:

- Domain objects should not depend on FastAPI, SQLAlchemy, pandas, or provider SDKs.
- Derived values must be distinguishable from source values.
- Unsupported claims must not be inferred during preprocessing.

### 7.3 Work Package 1.2: Database Schema and Migrations

Tasks:

- Create `dataset_versions` with staging, validated, active, failed, and retired states.
- Create `restaurants` with version ownership and source traceability.
- Add cuisine storage using a normalized relation or PostgreSQL array based on measured volume.
- Create `budget_profiles` with currency and configuration version.
- Add uniqueness, range, and referential-integrity constraints.
- Add indexes for version, location, rating, cost, currency, and cuisine filtering.
- Create an atomic activation operation ensuring only one dataset version is active.
- Add downgrade or forward-recovery procedures for each migration.

Tests:

- Migrations apply to an empty database.
- Schema constraints reject invalid records.
- Only one active dataset version is possible.
- A failed staging load cannot alter the active version.

### 7.4 Work Package 1.3: Dataset Adapter

Tasks:

- Implement a Hugging Face dataset adapter.
- Accept a source revision or record the resolved revision.
- Capture dataset name, split, schema, source revision, and content hash.
- Support a local fixture adapter for tests and offline development.
- Map source rows to an intermediate raw-record contract.
- Classify download, schema, and decoding failures with stable error codes.

Tests:

- Fixture adapter is deterministic.
- Unknown or missing columns fail before publication.
- Re-running the same revision and content is idempotent.

### 7.5 Work Package 1.4: Normalization and Validation Pipeline

Tasks:

- Normalize names, cities, localities, and cuisine lists.
- Parse rating and retain the source rating scale.
- Parse cost into minor units only when currency and units are known.
- Normalize missing and placeholder values.
- Detect exact and policy-defined duplicate records.
- Calculate source-payload hashes.
- Separate accepted and rejected records.
- Produce reason codes for rejected or partially usable rows.
- Produce a quality report with counts and field coverage.

Required tests:

- Case, whitespace, punctuation, and delimiter variants.
- Multiple cuisines in one field.
- Decimal and malformed ratings.
- Formatted, missing, negative, and ambiguous costs.
- Duplicate records with matching and conflicting values.
- Missing location, cuisine, rating, and cost.
- Unicode restaurant and locality names.

### 7.6 Work Package 1.5: Staging, Validation, and Publication

Tasks:

- Create a new staging dataset version for each unique ingestion.
- Bulk-load normalized records within bounded transactions.
- Run database-level verification after loading.
- Enforce configurable quality gates.
- Mark the version validated only after every gate succeeds.
- Atomically activate the validated version.
- Retain the previous active version for rollback.
- Mark failed versions with a safe quality report.
- Add an operator command to list, activate, and inspect versions.

Quality gates should include:

- Required schema present.
- Accepted row count in the expected range.
- Unique source keys within the version.
- Ratings within scale.
- Non-negative comparable costs.
- Known currency for budget-filterable records.
- Location and cuisine coverage above agreed thresholds.
- Rejection and duplicate rates below agreed limits.

### 7.7 Work Package 1.6: Ingestion Operations

Tasks:

- Add structured job logging and a generated job ID.
- Record ingestion duration and record-count metrics.
- Document manual execution and failure recovery.
- Add a dry-run mode that profiles and validates without publishing.
- Define dataset version retention without automatically deleting data during activation.
- Add a rollback runbook for reactivating the prior version.

### 7.8 Phase 1 Deliverables

- Canonical domain model.
- Database migrations and indexes.
- Hugging Face and fixture adapters.
- Normalization and data-quality modules.
- Versioned staging and atomic publication commands.
- Data-quality report and operator documentation.
- Unit and database integration tests.

### 7.9 Phase 1 Exit Criteria

- A pinned source revision can be ingested from start to finish.
- Re-running the same ingestion is safe and idempotent.
- Invalid data is rejected or marked unavailable according to documented rules.
- A failed load leaves the current active version unchanged.
- The prior dataset version can be reactivated.
- Database queries return normalized restaurant records from the active version.
- Phase 1 tests pass in CI using an ephemeral PostgreSQL instance.

## 8. Phase 2: Deterministic Recommendation API

### 8.1 Objective

Deliver a complete API that accepts preferences, enforces hard constraints, ranks candidates deterministically, and returns useful results without depending on an LLM.

This phase implements FR-03, FR-04, FR-05, the deterministic part of FR-06, FR-09, FR-10, FR-11, and FR-12.

### 8.2 Work Package 2.1: API Contracts

Tasks:

- Define Pydantic request and response models.
- Represent location, budget, cuisines, minimum rating, free-form preference, and result count explicitly.
- Use cost in integer minor units in external contracts where numeric values are returned.
- Set maximum lengths and collection sizes.
- Define stable error envelopes and error codes.
- Version routes under `/api/v1`.
- Generate and review OpenAPI documentation.
- Add contract examples for standard, no-match, fallback-ready, and invalid requests.

Validation rules:

- Location is required unless an explicitly documented default is enabled.
- Minimum rating falls within the active dataset scale.
- Budget ranges are ordered and use a supported currency.
- Cuisine lists are bounded and deduplicated.
- Free-form preferences have a strict length limit.
- Result count has a default and an enforced maximum.

### 8.3 Work Package 2.2: Preference Normalization

Tasks:

- Build the canonical `RecommendationQuery`.
- Normalize city, locality, and cuisines using the same rules as ingestion.
- Resolve named budget tiers from versioned `budget_profiles`.
- Record defaults and interpretations for the response.
- Keep free-form preferences as soft, untrusted data.
- Reject ambiguous or unsupported currencies rather than making hidden conversions.

Tests:

- Equivalent spellings normalize consistently.
- Named budgets resolve deterministically.
- Invalid rating, budget, and result-count boundaries are rejected.
- Empty optional fields broaden results without failing.

### 8.4 Work Package 2.3: Repository Queries

Tasks:

- Implement the restaurant repository interface.
- Filter by active dataset, city, optional locality, comparable budget, minimum rating, and cuisine.
- Treat missing fields as failing a related hard constraint.
- Set an absolute filtered-record ceiling.
- Add stable ordering before application scoring.
- Implement location, cuisine, and budget metadata lookups.
- Inspect query plans using representative dataset volume.

Security and performance:

- Use parameterized queries only.
- Prevent wildcard abuse in metadata search.
- Bound every list endpoint.
- Confirm indexes are used for common filter combinations.

### 8.5 Work Package 2.4: Deterministic Scoring

Tasks:

- Implement normalized location, cuisine, budget, rating, confidence, and completeness terms.
- Implement the documented weighted score.
- Use confidence-adjusted rating when vote counts exist.
- Version scoring weights and constants.
- Add stable tie-breakers.
- Limit the scored candidate list to the configured ceiling.
- Provide a score explanation object for debugging and evaluation, without exposing internal detail by default.

Tests:

- Every term stays within `[0, 1]`.
- Scores are repeatable for identical inputs and configuration.
- Tie-breakers produce stable ordering.
- Higher minimum rating cannot admit lower-rated records.
- Candidates violating a hard constraint never reach scoring.

### 8.6 Work Package 2.5: Safe Template Explanations

Tasks:

- Generate deterministic explanations from verified facts.
- Mention cuisine, budget, rating, and location only when available and relevant.
- Add caveats for unverifiable free-form preferences.
- Never claim family suitability, ambience, or service speed without supporting fields.
- Mark the response mode as `fallback` or `deterministic` until Phase 3 introduces LLM mode.

### 8.7 Work Package 2.6: No-Match and Relaxation Analysis

Tasks:

- Return a clear no-match outcome when hard constraints eliminate every record.
- Count independently relaxed alternatives without applying them.
- Support proposed relaxation categories for locality, budget, rating, and cuisine.
- State exactly which constraint would change and how many candidates it would produce.
- Avoid combinatorial relaxation searches in the initial version.
- Require a new request or explicit user permission before returning relaxed recommendations.

Tests:

- No-match results do not contain recommendations.
- Each relaxation count matches an independently executed query.
- Original constraints remain unchanged.
- Missing data does not appear as a relaxed match unless policy explicitly permits it.

### 8.8 Work Package 2.7: API Endpoints and Error Mapping

Implement:

- `POST /api/v1/recommendations`
- `GET /api/v1/metadata/locations`
- `GET /api/v1/metadata/cuisines`
- `GET /api/v1/metadata/budgets`
- `GET /health/live`
- `GET /health/ready`

Tasks:

- Keep route handlers thin.
- Generate and return request IDs.
- Map validation, repository, dataset, and internal errors to stable API codes.
- Return the active dataset and scoring configuration versions.
- Report LLM status as degraded without failing readiness when deterministic mode works.

### 8.9 Work Package 2.8: Verification

Add:

- Unit tests for normalization, filters, scoring, explanations, and relaxations.
- Property-based tests for hard-constraint and membership invariants.
- Repository integration tests with PostgreSQL.
- OpenAPI contract tests.
- API integration tests with a known dataset fixture.
- Basic performance measurement for common and worst-case filters.

### 8.10 Phase 2 Deliverables

- Versioned recommendation and metadata APIs.
- Deterministic ranking and factual explanations.
- Transparent no-match and relaxation behavior.
- Readiness and liveness probes.
- OpenAPI contract and API usage documentation.
- Automated unit, property, integration, and contract tests.

### 8.11 Phase 2 Exit Criteria

- Valid preference requests return ranked, source-grounded restaurants.
- 100% of returned records satisfy all hard constraints in automated tests.
- Identical input, active dataset, and scoring configuration produce identical ordering.
- No-match requests return clear, accurate relaxation options without applying them.
- Missing or invalid source fields are never fabricated.
- Dataset failure, invalid input, and internal failure map to documented errors.
- The API remains fully useful without an LLM.

## 9. Phase 3: Grounded LLM Ranking and Explanations

### 9.1 Objective

Add personalized LLM ranking and narrative explanations without weakening deterministic eligibility, factual correctness, availability, or testability.

This phase completes FR-06, FR-07, FR-08, FR-11, and LLM-related parts of FR-12.

### 9.2 Work Package 3.1: Provider-Neutral Ranking Contract

Tasks:

- Define `RankingRequest`, `RankingCandidate`, and `RankingResult` domain contracts.
- Define the asynchronous `RankingModel` protocol.
- Implement a deterministic fake model for development and tests.
- Select and implement the first provider adapter.
- Capture provider model ID, provider request ID, token usage, and categorized failures.
- Keep SDK types inside the infrastructure adapter.

### 9.3 Work Package 3.2: Prompt Design

Tasks:

- Create a versioned system instruction template.
- Delimit user preferences and candidate JSON as untrusted data.
- Include restaurant IDs and only whitelisted attributes.
- Explicitly prohibit new candidates and unsupported facts.
- Require caveats for unverified soft preferences.
- Require a strict structured output schema.
- Set a low-variance generation configuration and bounded output length.
- Store prompt templates in `docs/prompts/` or a versioned application resource.
- Add prompt change notes and rollback instructions.

The model should return only:

- Ordered candidate IDs.
- Explanations tied to supplied evidence.
- Caveats.
- An optional concise comparison summary.

It must not return authoritative copies of restaurant facts.

### 9.4 Work Package 3.3: Candidate Preparation

Tasks:

- Pre-rank all eligible candidates deterministically.
- Send only the configured top candidate count to the model.
- Serialize candidates consistently to improve cacheability and evaluation.
- Exclude source fields that are unnecessary or unsafe.
- Estimate or enforce prompt-size limits.
- Record candidate IDs and configuration versions for audits.

### 9.5 Work Package 3.4: Response Guard

Tasks:

- Parse provider output into the strict internal schema.
- Reject unknown, missing, or duplicate restaurant IDs.
- Enforce the requested result count.
- Validate that all IDs came from the submitted candidate set.
- Ignore any model-supplied factual copies.
- Rehydrate name, location, cuisine, rating, and cost from candidate records.
- Enforce explanation and caveat length limits.
- Ensure generated text is rendered as text, not raw HTML.
- Allow one bounded structured repair attempt for malformed output.
- Route persistent validation failure to deterministic fallback.

Adversarial tests:

- Unknown restaurant insertion.
- Modified rating or cost.
- Duplicate IDs.
- Too many results.
- Missing required fields.
- Markdown or HTML injection.
- Instructions embedded in user text or restaurant data.
- Refusal, empty response, and truncated JSON.

### 9.6 Work Package 3.5: Orchestration and Fallback

Tasks:

- Integrate ranking after deterministic eligibility and scoring.
- Set an end-to-end LLM deadline.
- Retry only documented transient failures with bounded backoff.
- Add an in-process circuit breaker initially or use a shared implementation if multiple instances require it.
- Fall back immediately when the circuit is open.
- Return `mode: "llm"` only after complete output validation.
- Return `mode: "fallback"` with safe template explanations otherwise.
- Preserve the original HTTP success when fallback produces valid recommendations.
- Return warnings that are useful to users without exposing provider internals.

### 9.7 Work Package 3.6: Recommendation Audit Metadata

Tasks:

- Add the `recommendation_audits` schema or an equivalent telemetry sink.
- Record request ID, dataset version, scoring version, prompt version, model ID, candidate IDs, returned IDs, mode, timing, token usage, and failure category.
- Hash the canonical query key.
- Exclude raw free-form preferences by default.
- Define retention and access policy before enabling production persistence.

### 9.8 Work Package 3.7: Offline Evaluation Suite

Tasks:

- Create representative user profiles covering locations, budgets, cuisines, ratings, missing preferences, and ambiguous soft requests.
- Define eligibility assertions independent of the model.
- Create a human-review rubric for ranking relevance and explanation evidence.
- Measure unknown-ID rate, factual consistency, unsupported claims, schema validity, latency, token usage, and estimated cost.
- Compare LLM order with deterministic baseline.
- Store evaluation runs by dataset, prompt, scoring, and model version.
- Establish pass/fail thresholds for prompt or model changes.

Required hard gates:

- Unknown restaurant rate after validation: 0%.
- Hard-constraint violation rate: 0%.
- Altered factual fields reaching API output: 0%.
- Successful deterministic fallback when candidates exist: 100% in simulated provider failures.

### 9.9 Phase 3 Deliverables

- Provider-neutral model interface and first adapter.
- Versioned structured prompt.
- Candidate serializer and prompt-size controls.
- Response guard and trusted-field rehydration.
- Timeout, retry, circuit-breaker, repair, and fallback behavior.
- Audit metadata and LLM operational metrics.
- Versioned offline evaluation suite and baseline report.

### 9.10 Phase 3 Exit Criteria

- The model can rank only submitted candidate IDs.
- All returned factual fields come from trusted records, not generated text.
- Malformed and adversarial output cannot bypass validation.
- Provider timeouts and failures return deterministic results when candidates exist.
- Prompt and model versions are visible in telemetry and evaluation records.
- The selected prompt and model pass the agreed evaluation thresholds.
- LLM-specific secrets remain server-side and out of logs.

## 10. Phase 4: End-User Web Experience

### 10.1 Objective

Deliver an accessible, responsive interface for collecting preferences, understanding interpreted constraints, comparing recommendations, and recovering from no-match or error states.

This phase exposes FR-03 through FR-12 to end users.

### 10.2 Work Package 4.1: UX Flow and Component Design

Define screens and states for:

- Initial preference entry.
- Client and server validation errors.
- Recommendation loading.
- Ranked results.
- No exact match and proposed relaxations.
- Deterministic fallback mode.
- Dataset or service failure.
- Empty and unsupported-location states.

Tasks:

- Define the information hierarchy for result cards.
- Visibly distinguish facts, AI explanations, and caveats.
- Decide how applied defaults and interpreted preferences are shown.
- Avoid presenting dataset values as live availability.
- Add the dataset limitation disclosure in an unobtrusive but visible location.

### 10.3 Work Package 4.2: Typed API Client

Tasks:

- Generate or implement TypeScript types from OpenAPI.
- Create a single API client boundary.
- Propagate request IDs into supportable error displays.
- Map stable error codes to actionable UI messages.
- Add request cancellation when the user changes or abandons a search.
- Avoid automatic retry of invalid requests.

### 10.4 Work Package 4.3: Preference Form

Tasks:

- Implement location controls backed by metadata search.
- Implement multi-select cuisine controls.
- Implement budget tier or explicit range input based on product choice.
- Implement minimum rating and result-count controls.
- Implement bounded additional-preference text input.
- Add client validation consistent with, but not replacing, server validation.
- Make optional and required inputs explicit.
- Preserve user input when validation fails.

### 10.5 Work Package 4.4: Recommendation Results

Each result should display:

- Rank and restaurant name.
- Location.
- Cuisines.
- Rating and rating scale.
- Estimated cost with currency-aware formatting.
- Grounded explanation.
- Caveats for unsupported preferences.

Tasks:

- Display response mode when fallback affects explanation quality.
- Display the interpreted preferences and any defaults.
- Display explicit relaxations separately from exact matches.
- Avoid color-only status indicators.
- Safely render explanation text without raw HTML.
- Add a simple repeat-search or edit-preferences path.

### 10.6 Work Package 4.5: Accessibility and Responsive Behavior

Tasks:

- Use semantic form labels, headings, lists, and buttons.
- Support keyboard-only operation.
- Manage focus after validation, result loading, and route transitions.
- Use an appropriate live region for asynchronous status without excessive announcements.
- Meet contrast and target-size requirements.
- Support screen zoom and narrow mobile layouts.
- Ensure rating and cost meaning is present in text.

### 10.7 Work Package 4.6: Frontend Testing

Add:

- Component tests for forms, validation, cards, caveats, and errors.
- API client contract tests.
- Browser E2E tests for standard search, no-match, fallback, invalid input, and server errors.
- Automated accessibility checks.
- Manual keyboard and screen-reader smoke testing.
- Responsive tests at representative breakpoints.

### 10.8 Phase 4 Deliverables

- Complete preference form and metadata-assisted inputs.
- Ranked result comparison interface.
- Interpreted preference, caveat, relaxation, fallback, and error displays.
- Typed API client.
- Component, E2E, and accessibility tests.

### 10.9 Phase 4 Exit Criteria

- A user can submit all supported preferences and receive recommendations.
- Validation errors are specific and preserve entered data.
- Facts, generated explanations, and caveats are distinguishable.
- No-match and fallback outcomes remain useful and understandable.
- Core flows work on keyboard, mobile viewport, and supported screen readers.
- Generated text is never rendered as trusted HTML.
- Browser E2E and accessibility checks pass in CI.

## 11. Phase 5: Production Readiness

### 11.1 Objective

Make the system secure, observable, resilient, cost-controlled, and deployable through repeatable automation.

This phase completes the non-functional requirements in the problem statement.

### 11.2 Work Package 5.1: Shared Cache

Tasks:

- Add Redis through a cache interface.
- Build a canonical cache key from dataset, scoring, prompt, model, normalized query, free-text hash, and result count.
- Cache only fully validated responses.
- Configure bounded TTLs.
- Cache metadata separately.
- Treat cache failures as misses.
- Measure hit rate and avoided model calls.
- Confirm dataset activation naturally changes keys.

### 11.3 Work Package 5.2: Rate Limiting and Abuse Controls

Tasks:

- Define anonymous per-IP or authenticated-account limits.
- Apply tighter controls to recommendation creation than metadata lookup.
- Limit body size, free-text length, cuisine count, and result count at the edge and application.
- Return consistent `429` responses with safe retry guidance.
- Monitor rejected traffic without storing unnecessary personal data.

### 11.4 Work Package 5.3: Security Hardening

Tasks:

- Configure TLS and secure ingress headers.
- Move secrets into the deployment secret manager.
- Create separate least-privilege database identities for migrations, API reads, audits, and ingestion writes.
- Restrict outbound traffic where the platform supports it.
- Review CORS, trusted hosts, and proxy behavior.
- Add dependency, container, and secret scans to release gates.
- Generate an SBOM.
- Perform prompt-injection, SQL-injection, XSS, and denial-of-service tests.
- Complete a lightweight threat model and remediation review.

### 11.5 Work Package 5.4: Observability

Tasks:

- Add OpenTelemetry traces across API, repository, cache, model, validation, and ingestion operations.
- Add structured logs with correlation IDs and version metadata.
- Add the metrics defined in the architecture.
- Create dashboards for traffic, latency, failures, fallback rate, no-match rate, cache hit rate, provider usage, and ingestion quality.
- Create alerts for service availability, database saturation, validation failures, provider errors, and ingestion regressions.
- Confirm prompts, credentials, and raw free-form text are absent from telemetry.

### 11.6 Work Package 5.5: Reliability Controls

Tasks:

- Tune database, cache, and provider timeouts.
- Validate retry classification and retry budgets.
- Exercise the circuit breaker under failure injection.
- Add graceful shutdown behavior.
- Verify connection pool sizing under load.
- Validate deterministic fallback with Redis and the provider unavailable.
- Define behavior when no active dataset exists.

### 11.7 Work Package 5.6: Deployment Automation

Tasks:

- Build reproducible, minimal runtime images.
- Run containers as a non-root user where supported.
- Configure development, staging, and production separately.
- Automate migrations with a dedicated identity.
- Deploy the web artifact through a CDN or static host.
- Deploy stateless API instances behind managed ingress.
- Deploy ingestion as an on-demand or scheduled job.
- Add rolling or canary release strategy.
- Promote the same tested artifact between environments.
- Document application, migration, and dataset rollback procedures.

### 11.8 Work Package 5.7: Backup and Recovery

Tasks:

- Enable database backups and point-in-time recovery.
- Test restoration into an isolated environment.
- Verify rollback to a previous dataset version.
- Document recovery objectives and responsible roles.
- Confirm audit and telemetry retention behavior.
- Define safe cleanup for retired dataset versions.

### 11.9 Work Package 5.8: Performance and Cost Validation

Tasks:

- Load-test common, broad, no-match, and worst-case queries.
- Measure non-LLM and end-to-end percentiles.
- Inspect slow database queries.
- Measure prompt sizes, output tokens, cache impact, and estimated cost per request.
- Tune candidate ceilings and timeouts without weakening relevance gates.
- Verify horizontal API scaling and shared rate limiting.
- Establish budgets and alerts for provider spend.

### 11.10 Phase 5 Deliverables

- Production container and deployment definitions.
- Shared cache and rate limiting.
- Hardened secrets, networking, and database access.
- Dashboards, alerts, traces, and runbooks.
- Backup and restore evidence.
- Load, resilience, cost, and security test reports.
- Automated staging and production delivery pipeline.

### 11.11 Phase 5 Exit Criteria

- Staging deployment is reproducible from CI/CD.
- Secrets are managed outside code and client artifacts.
- The service meets agreed load and latency thresholds in staging.
- Provider, cache, and database failure scenarios behave as documented.
- Dashboards and alerts identify actionable failures.
- Backup restoration and dataset rollback have been tested.
- Critical and high security findings are resolved or formally accepted.
- The release artifact and migration path have a tested rollback.

## 12. Phase 6: Release Validation and Launch

### 12.1 Objective

Verify the full system against product acceptance criteria, release it safely, and establish a measured improvement loop.

### 12.2 Work Package 6.1: Requirements Traceability Review

Tasks:

- Map FR-01 through FR-12 to tests and deployed behavior.
- Map all ten problem-statement acceptance criteria to evidence.
- Confirm non-goals have not entered the release unintentionally.
- Review user-facing disclosures about dataset freshness and unsupported attributes.
- Close or explicitly defer unresolved gaps.

### 12.3 Work Package 6.2: Release Candidate Validation

Run the full release suite:

- Unit, property, integration, contract, and E2E tests.
- Offline recommendation evaluation.
- Accessibility verification.
- Performance and soak tests.
- Dependency, container, API, and prompt-injection security tests.
- Migration rehearsal from the current production-equivalent schema.
- Backup restoration and rollback rehearsal.
- Manual smoke tests using representative user profiles.

### 12.4 Work Package 6.3: Operational Readiness Review

Confirm:

- Dashboards and alerts are active.
- On-call or responsible owners are assigned.
- Dataset failure, provider outage, high latency, cost spike, and rollback runbooks are accessible.
- Provider quotas and budget alerts are configured.
- Support can locate a request using its request ID without viewing sensitive text.
- Data and log retention settings match policy.

### 12.5 Work Package 6.4: Controlled Launch

Tasks:

- Deploy the release candidate to production using canary or limited traffic.
- Monitor errors, latency, invalid model output, fallback rate, cache performance, and costs.
- Compare production behavior with staging baselines.
- Increase traffic only when gates remain healthy.
- Roll back on agreed threshold breaches.
- Record the deployed application, dataset, scoring, prompt, and model versions.

### 12.6 Work Package 6.5: Post-Launch Hardening

During the initial observation window:

- Review no-match patterns and unsupported locations.
- Review aggregate relaxation usage.
- Sample explanations through the approved privacy-safe evaluation process.
- Add regression tests for confirmed defects.
- Tune scoring and prompt behavior only through versioned evaluation and release.
- Revisit candidate count, cache TTL, rate limits, and provider cost using actual measurements.
- Prioritize future work using user value and measured system gaps.

### 12.7 Phase 6 Exit Criteria

- All release acceptance criteria have test or operational evidence.
- The controlled launch completes without unresolved severe regressions.
- Hard-constraint violations and unknown restaurant IDs remain at 0% after validation.
- Production fallback works during a controlled provider-failure test.
- Ownership, monitoring, runbooks, and rollback mechanisms are active.
- A documented backlog exists for post-MVP improvements.

## 13. Requirements Traceability Matrix

| Requirement | Primary implementation phase | Verification |
|---|---|---|
| FR-01 Dataset loading | Phase 1 | Adapter and ingestion integration tests |
| FR-02 Data preprocessing | Phase 1 | Normalization unit tests and quality report |
| FR-03 Preference input | Phases 2 and 4 | API contract and browser E2E tests |
| FR-04 Input validation | Phases 2 and 4 | Boundary, contract, and UI validation tests |
| FR-05 Candidate filtering | Phase 2 | Repository, property-based, and API tests |
| FR-06 Candidate ranking | Phases 2 and 3 | Score tests and offline ranking evaluation |
| FR-07 Grounded explanations | Phase 3 | Evidence rubric and adversarial tests |
| FR-08 Structured output validation | Phase 3 | Response-guard and hallucination tests |
| FR-09 No-match handling | Phases 2 and 4 | API and E2E no-match scenarios |
| FR-10 Partial-data handling | Phases 1, 2, and 4 | Data fixtures, API tests, and UI display tests |
| FR-11 Repeatable requests | Phases 2, 3, and 5 | Deterministic tests and versioned cache tests |
| FR-12 Error handling | All implementation phases | Failure injection and E2E error scenarios |

## 14. Milestone Demonstrations

Each phase should end with a short demonstration using a fixed, documented scenario.

### Milestone 0: Runnable Skeleton

- Start the repository locally.
- Open the web shell.
- Call API liveness.
- Show CI passing.

### Milestone 1: Trusted Dataset

- Ingest the fixture and source dataset.
- Inspect the quality report.
- Activate a version.
- Demonstrate rollback to a prior version.

### Milestone 2: Deterministic Product

- Request restaurants with location, cuisine, budget, and rating.
- Show that every result satisfies all filters.
- Show a no-match request and its relaxation counts.
- Disable external network access and repeat a successful request.

### Milestone 3: Grounded AI

- Show LLM-reordered eligible candidates.
- Demonstrate that factual fields are rehydrated.
- Inject an unknown ID in the fake model response and show rejection/fallback.
- Trigger a provider timeout and show deterministic results.

### Milestone 4: End-User Experience

- Complete a recommendation journey on desktop and mobile.
- Navigate the flow using only a keyboard.
- Show exact match, no-match, fallback, and validation-error states.

### Milestone 5: Production Readiness

- Show dashboards during a load test.
- Trigger circuit-breaker and cache failure scenarios.
- Demonstrate deployment and rollback in staging.
- Restore the database into an isolated environment.

### Milestone 6: Controlled Release

- Show version identifiers for the live release.
- Review canary health and cost metrics.
- Confirm the launch checklist and rollback decision path.

## 15. Dependency and Parallelization Guide

The following work can proceed in parallel without weakening sequencing:

- Phase 1 database migrations and normalization logic can proceed after the canonical model is agreed.
- During Phase 2, metadata endpoints, scoring logic, and API contract implementation can proceed independently against shared fixtures.
- During Phase 3, prompt evaluation cases can be authored while the provider adapter and response guard are built.
- Phase 4 design and web scaffolding can begin after the Phase 2 API contract stabilizes.
- Phase 5 deployment foundations and telemetry infrastructure can begin earlier, but production gates must use completed Phases 1-4.

The following dependencies are strict:

- Do not implement authoritative filters before dataset semantics are known.
- Do not send candidates to an LLM before deterministic filtering is correct.
- Do not expose model output before response guarding and rehydration are complete.
- Do not enable response caching before versioned cache keys are defined.
- Do not release before deterministic fallback, rollback, and operational monitoring are tested.

## 16. Definition of Done for Every Work Package

A work package is done only when:

- Its behavior is implemented behind the intended module boundary.
- Applicable unit and integration tests pass.
- Error paths and boundary cases are tested.
- Logs and metrics are sufficient to diagnose failure.
- Security and privacy implications have been considered.
- Configuration and operational behavior are documented.
- API or data-contract changes are reflected in schemas and examples.
- No unresolved critical defect remains.
- The change passes CI and is demonstrable in the target environment.

## 17. MVP Completion Criteria

The MVP is complete after Phase 5 and ready for the Phase 6 controlled release when:

1. A pinned dataset revision can be safely ingested, validated, activated, and rolled back.
2. Users can submit all supported structured and free-form preferences.
3. Deterministic code enforces every hard constraint.
4. The LLM ranks only a bounded eligible candidate set.
5. Every factual value is rehydrated from trusted data.
6. Unknown or malformed LLM output is rejected.
7. Provider failure returns useful deterministic recommendations.
8. No-match and unsupported-preference outcomes are transparent.
9. The accessible web interface supports core desktop and mobile flows.
10. Security, telemetry, backup, deployment, and rollback controls are operational.
11. Automated tests cover normal, boundary, adversarial, and failure cases.
12. The system meets the agreed relevance, grounding, latency, reliability, and cost gates.
