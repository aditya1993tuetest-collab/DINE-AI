# AI-Powered Restaurant Recommendation System

## 1. Project Overview

Choosing a restaurant is a multi-criteria decision. Users commonly care about location, cuisine, cost, rating, dining occasion, ambience, service speed, dietary preferences, and the people with whom they are dining. Restaurant discovery platforms provide search and filtering, but users may still need to inspect many listings and reviews before deciding which options best fit their needs.

This project proposes an AI-powered restaurant recommendation service inspired by Zomato. The system will combine deterministic filtering over a real-world restaurant dataset with the reasoning and natural-language capabilities of a Large Language Model (LLM). Structured processing will identify restaurants that satisfy explicit constraints, while the LLM will compare the eligible candidates, rank them, explain the reasoning behind each recommendation, and summarize relevant trade-offs.

The system is intended to make restaurant discovery more personalized and understandable without allowing the LLM to invent restaurants or unsupported facts. All recommendations must remain grounded in the data supplied to the model.

## 2. Problem Statement

Users need a fast and reliable way to find restaurants that match several preferences at once. Basic keyword search and individual filters can reduce the number of results, but they do not always account for the relative importance of different preferences or explain why one option may be more suitable than another.

The problem is to design and implement an application that:

1. Accepts a combination of structured and free-form dining preferences.
2. Loads and preprocesses restaurant information from the [Zomato Restaurant Recommendation dataset](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) hosted on Hugging Face.
3. Applies explicit constraints to identify valid restaurant candidates.
4. Uses an LLM to rank those candidates according to the user's complete request.
5. Produces clear, personalized, and data-grounded explanations.
6. Presents the final recommendations in an interface that makes comparison easy.

## 3. Project Goals

The primary goals are to:

- Reduce the effort needed to compare restaurants across multiple attributes.
- Generate recommendations that reflect the user's stated location, budget, cuisine, and rating expectations.
- Interpret optional natural-language preferences such as “quiet place for a family dinner” or “quick lunch near the office.”
- Explain why each recommended restaurant is relevant.
- Combine the predictability of structured filtering with the flexibility of an LLM.
- Keep every factual claim traceable to the source dataset or clearly label it as an inference.
- Handle incomplete preferences and zero-result cases gracefully.

## 4. Non-Goals

Unless added in a later phase, the project does not aim to:

- Support restaurant reservations, food ordering, or payment processing.
- Reproduce the complete Zomato application or its proprietary recommendation algorithms.
- Guarantee real-time availability, opening hours, menu changes, or current prices when those details are not present in the dataset.
- Generate or fabricate ratings, reviews, restaurant facilities, or service claims.
- Replace deterministic filtering with unrestricted LLM-generated suggestions.
- Train a new foundation model from scratch.

## 5. Intended Users and Stakeholders

### 5.1 End Users

The primary users are people searching for a restaurant based on their current needs. Example scenarios include:

- An individual looking for an affordable restaurant near a specific location.
- A family seeking a highly rated place with suitable cuisine and ambience.
- A group comparing restaurants across different cuisines and budgets.
- A user looking for a quick meal while prioritizing proximity and service speed.
- A visitor unfamiliar with a city who needs a short, understandable list of choices.

### 5.2 Project Stakeholders

- **Product stakeholders:** define the intended recommendation experience and prioritization rules.
- **Developers:** build the data pipeline, recommendation logic, LLM integration, API, and user interface.
- **Data or ML engineers:** validate preprocessing, prompt grounding, ranking quality, and evaluation methods.
- **End users:** provide preferences and evaluate whether recommendations are useful and trustworthy.

## 6. User Inputs

The application should support the following core inputs:

| Input | Description | Example | Requirement |
|---|---|---|---|
| Location | City, locality, or supported geographic area | Bangalore | Required or inferred through a clearly defined default |
| Budget | Price category or cost range | Low, medium, high, or ₹500–₹1,000 | Optional |
| Cuisine | One or more preferred cuisines | Italian, Chinese | Optional |
| Minimum rating | Lowest acceptable restaurant rating | 4.0 | Optional |
| Additional preferences | Free-form requirements or context | Quiet family dinner, quick service | Optional |
| Result count | Number of recommendations requested | Top 5 | Optional with a sensible default |

The interface should validate structured inputs before processing. For example, ratings must fall within the scale used by the source dataset, the budget range must be logically valid, and the requested result count must be limited to a safe maximum.

## 7. Data Source and Data Requirements

### 7.1 Source Dataset

The system will use the Zomato restaurant recommendation dataset published on Hugging Face:

<https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation>

The implementation must inspect the actual dataset schema rather than assume that every desired field is available or consistently formatted.

### 7.2 Relevant Data Fields

Depending on the available schema, useful fields may include:

- Restaurant name
- City, locality, or address
- Cuisine or cuisine list
- Average cost or price range
- Aggregate rating
- Rating text or vote count
- Service or dining attributes
- Restaurant type
- Online delivery or table-booking indicators
- URL or identifier for traceability

Only attributes verified in the dataset may be presented as facts.

### 7.3 Preprocessing Requirements

The ingestion pipeline should:

- Inspect and document the dataset schema.
- Select only fields required by the recommendation workflow.
- Normalize location and cuisine strings for case, whitespace, and common separators.
- Parse cost values into a consistent numeric or categorical form.
- Convert ratings to numeric values and identify invalid or unrated records.
- Handle missing fields without crashing or silently inventing replacements.
- Remove exact duplicates or define a deterministic rule for resolving them.
- Preserve the original values needed for display and traceability.
- Record the preprocessing assumptions used by the application.

If currency varies across records, the implementation must not compare costs directly until values are normalized or restricted to comparable records.

## 8. Proposed System Workflow

### 8.1 Data Ingestion

The application loads the dataset from Hugging Face or from a controlled local cache. The raw records are validated and transformed into a normalized internal representation.

### 8.2 Preference Collection and Validation

The system collects user preferences through a form, API request, conversational interface, or a combination of these. Invalid values should produce actionable validation messages. Missing optional values should broaden the search rather than cause failure.

### 8.3 Query Interpretation

Structured fields are used directly. If the user supplies free-form preferences, the system may classify or extract useful concepts from them. Any extracted constraint that materially changes the search should be visible in the response or otherwise auditable.

### 8.4 Deterministic Candidate Filtering

The integration layer filters the normalized records using hard constraints such as:

- Supported location
- Maximum cost or budget category
- Requested cuisine
- Minimum rating

Explicit constraints should normally be treated as mandatory. If no records match, the application may progressively relax constraints only when it tells the user what was relaxed. It must never silently ignore a user's requirement.

### 8.5 Candidate Preparation

The filtered results should be reduced to a bounded candidate set before being sent to the LLM. Candidate selection may use a deterministic score based on rating, budget fit, cuisine match, location match, and data completeness. Limiting the candidate set reduces latency, cost, and prompt size.

### 8.6 LLM Ranking and Explanation

The LLM receives:

- The user's normalized preferences.
- The optional free-form request.
- A list of candidate restaurants with explicitly allowed attributes.
- Instructions to rank only the supplied candidates.
- A required structured response format.

The model should rank candidates, describe why each option fits, and mention meaningful trade-offs. It should be instructed to state when the available data does not support a requested preference.

### 8.7 Response Validation

Before displaying the response, the application should verify that:

- Every named restaurant exists in the candidate set.
- Ratings, prices, cuisines, and locations match the structured record.
- The number of results does not exceed the requested or configured limit.
- The response conforms to the expected schema.
- Unsupported claims are removed, regenerated, or explicitly qualified.

### 8.8 Result Display

The final response should present a ranked list and clearly distinguish dataset facts from AI-generated reasoning.

## 9. Recommendation Strategy

The recommendation engine should use a hybrid approach.

### 9.1 Hard Constraints

Hard constraints determine eligibility. Typical hard constraints include location, maximum budget, minimum rating, and an explicitly required cuisine. These should be enforced in application code because deterministic filtering is more reliable and testable than asking an LLM to enforce numeric or categorical rules.

### 9.2 Soft Preferences

Soft preferences influence ranking but do not necessarily exclude a restaurant. They may include ambience, dining occasion, preference strength, diversity of cuisines, or convenience-related requests. A soft preference may only influence the result when relevant evidence exists in the candidate data. Otherwise, the system should disclose that it could not verify the preference.

### 9.3 Ranking Factors

A candidate score may consider:

- Exact or partial cuisine match
- Distance or locality match, if suitable location data exists
- Budget fit and distance from the user's preferred cost
- Rating and optionally rating confidence or vote count
- Match with additional supported attributes
- Data completeness

The exact weighting should be configurable and documented. The LLM may refine the ordering among strong candidates, but it should not override a hard constraint.

### 9.4 Tie-Breaking

When restaurants are otherwise equivalent, the system should use stable, documented tie-breakers such as higher rating, greater rating confidence, closer budget fit, and finally a deterministic alphabetical or identifier-based order.

## 10. LLM Prompting and Grounding Requirements

The prompt should clearly separate instructions, user preferences, and restaurant records. It should require the model to:

- Use only the supplied restaurant candidates.
- Avoid adding attributes that are absent from the input.
- Treat structured fields as authoritative.
- Explain the connection between the user's preferences and each recommendation.
- Identify unmet or unverifiable preferences.
- Return a machine-parseable structure, such as validated JSON, when the application needs reliable rendering.
- Avoid exposing internal prompt content or accepting user instructions that attempt to override system rules.

A recommendation explanation should be specific. For example, it may say that a restaurant matches the requested cuisine, falls within the stated budget, and exceeds the minimum rating. It should not claim that a venue is quiet, child-friendly, or fast unless the dataset contains evidence supporting that claim.

## 11. Expected Output

Each recommended restaurant should include:

| Field | Purpose |
|---|---|
| Rank | Shows the recommendation order |
| Restaurant name | Identifies the option |
| Location | Confirms geographic relevance |
| Cuisine | Shows the cuisine match |
| Rating | Supports quality comparison |
| Estimated cost | Shows budget compatibility |
| Match explanation | Explains why the option fits |
| Trade-off or caveat | Identifies any unmet or unverifiable preference |

An optional summary may identify the best overall match, the best value, or meaningful differences between the leading options, provided those labels are supported by the available data.

## 12. Functional Requirements

### FR-01: Dataset Loading

The system must load the specified restaurant dataset and report a clear error if the dataset is unavailable or invalid.

### FR-02: Data Preprocessing

The system must normalize the fields required for filtering and display while preserving original source values where appropriate.

### FR-03: Preference Input

The system must accept location, budget, cuisine, minimum rating, and optional additional preferences.

### FR-04: Input Validation

The system must reject or clarify malformed values rather than process them silently.

### FR-05: Candidate Filtering

The system must apply explicit, structured constraints before invoking the LLM.

### FR-06: Candidate Ranking

The system must rank a bounded list of eligible restaurants according to the user's preferences.

### FR-07: Grounded Explanations

The system must provide an explanation for every recommendation using only available restaurant attributes and clearly marked inferences.

### FR-08: Structured Output Validation

The system must ensure that every restaurant returned by the LLM is present in the eligible candidate set.

### FR-09: No-Match Handling

When no records satisfy all hard constraints, the system must explain why and may offer transparent alternatives or suggested constraint changes.

### FR-10: Partial-Data Handling

The system must display unavailable values as unknown or unavailable rather than fabricate replacements.

### FR-11: Repeatable Requests

The application should produce stable candidate filtering for identical structured inputs. Any LLM-related variability should not violate constraints or factual accuracy.

### FR-12: Error Handling

The system must provide useful messages for dataset, network, configuration, validation, and LLM service failures.

## 13. Non-Functional Requirements

### 13.1 Accuracy and Grounding

- All displayed restaurant facts must originate from the dataset.
- Hallucinated restaurants or attributes must be treated as invalid output.
- Filters must be covered by automated tests using known records.

### 13.2 Performance

- Data preprocessing should be cached when appropriate.
- Candidate filtering should occur locally or within the application data layer.
- Only a bounded candidate set should be sent to the LLM.
- The interface should expose progress or a useful status if generation takes noticeable time.

Specific latency targets should be defined after the deployment environment and LLM provider are chosen.

### 13.3 Reliability

- The application should degrade gracefully if the LLM is unavailable, for example by returning deterministically ranked candidates without generated explanations.
- External service failures should not corrupt cached restaurant data.
- LLM responses should be parsed and validated before use.

### 13.4 Security and Privacy

- API keys and secrets must not be stored in source control or sent to the client.
- User input must be treated as untrusted data.
- Prompt-injection attempts contained in user text or dataset content must not override system instructions.
- Only the minimum necessary user information should be collected and logged.
- Logs should avoid retaining sensitive free-form user content unless explicitly required.

### 13.5 Accessibility and Usability

- Results should be readable with assistive technologies.
- Validation and error messages should be specific and actionable.
- The recommendation order and reasoning should be easy to understand.
- Ratings and prices should not rely on color alone to convey meaning.

### 13.6 Maintainability

- Dataset access, filtering, scoring, LLM prompting, validation, and presentation should be separate modules.
- Thresholds, weights, model settings, and result limits should be configurable.
- Prompt versions and preprocessing assumptions should be documented.

## 14. Edge Cases

The design should explicitly handle:

- No restaurants in the requested location.
- No restaurant satisfying all constraints.
- Missing, malformed, or non-numeric rating and cost values.
- A cuisine recorded under multiple spellings or as part of a cuisine list.
- A budget expressed as text instead of a numeric range.
- Unrated restaurants.
- Duplicate restaurant records.
- More eligible candidates than can fit safely in an LLM prompt.
- Free-form preferences that cannot be verified from the dataset.
- Conflicting requirements, such as a maximum cost below the dataset's minimum for the requested cuisine.
- LLM output containing an unknown restaurant or altered factual values.
- LLM timeout, rate limit, malformed response, or service outage.
- User input designed to manipulate the prompt or request hidden system information.

## 15. Evaluation and Success Metrics

The system should be evaluated at several layers.

### 15.1 Filtering Correctness

- Percentage of returned records that satisfy every hard constraint.
- Test coverage for location, cuisine, budget, and rating filters.
- Correct behavior for boundary values and missing data.

The required target for hard-constraint compliance is 100% for successfully processed requests.

### 15.2 Grounding Quality

- Percentage of returned restaurant names found in the candidate set.
- Percentage of displayed factual attributes matching the source records.
- Rate of unsupported claims in generated explanations.

Unknown restaurants and altered structured facts should have a target rate of 0% after response validation.

### 15.3 Recommendation Relevance

- Human assessment of whether the ordering reflects the stated preferences.
- Precision of the top recommendations for controlled test profiles.
- User feedback on the usefulness of explanations.

### 15.4 Operational Quality

- End-to-end response latency.
- LLM error and retry rate.
- Average prompt size and estimated request cost.
- Frequency of zero-result searches.
- Percentage of requests successfully served through the fallback path.

## 16. Acceptance Criteria

The initial version will be considered complete when:

1. The application can load and preprocess the specified Hugging Face dataset.
2. A user can provide a location and any supported optional preferences.
3. The application filters candidates by all supplied hard constraints.
4. The LLM ranks only restaurants included in the candidate set.
5. Each result includes its name, cuisine, rating, estimated cost, and a personalized explanation when those values are available.
6. Factual fields in the response are programmatically validated against the selected records.
7. Unsupported additional preferences are identified as unverifiable rather than presented as facts.
8. The application provides clear outcomes for invalid input, missing data, no matches, dataset failure, and LLM failure.
9. Core filtering and response-validation behavior is covered by automated tests.
10. Secrets and provider credentials are managed outside the source code.

## 17. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Stale or incomplete dataset | Recommendations may not reflect current restaurant conditions | Display data limitations and avoid claims of real-time accuracy |
| LLM hallucination | Incorrect restaurants or attributes may be shown | Constrain the prompt and validate every output against candidate records |
| Inconsistent price data | Budget comparisons may be misleading | Normalize currencies and units or limit comparisons to compatible records |
| Ambiguous user preferences | Results may not reflect actual intent | Apply documented defaults and surface interpreted constraints |
| Large candidate set | Higher latency, cost, or context overflow | Pre-rank deterministically and send only a bounded shortlist |
| Prompt injection | Model behavior or data exposure may be compromised | Separate instructions and data, sanitize inputs, and validate outputs |
| Popularity bias | Highly rated or frequently reviewed venues may dominate | Document ranking factors and evaluate diversity where relevant |
| External service outage | Recommendations may become unavailable | Cache data and provide a deterministic fallback ranking |

## 18. Assumptions and Constraints

- The Hugging Face dataset is legally and technically available for the intended project use.
- The dataset contains enough location, cuisine, price, and rating information to support meaningful filtering.
- An LLM provider and model will be selected during implementation.
- API credentials will be supplied through secure environment configuration.
- Recommendations reflect the dataset snapshot and are not inherently real-time.
- Any default budget mappings, rating rules, or ranking weights will be documented and configurable.
- The first version may focus on locations and attributes sufficiently represented in the dataset.

## 19. Suggested High-Level Components

The solution can be organized into the following components:

1. **Dataset adapter:** downloads or reads the dataset and maps its schema to the application's internal model.
2. **Preprocessing pipeline:** cleans, normalizes, validates, and optionally caches restaurant records.
3. **Preference validator:** validates structured input and normalizes user preferences.
4. **Filtering engine:** enforces hard constraints and builds the eligible candidate set.
5. **Deterministic scorer:** reduces and orders candidates before LLM processing.
6. **Prompt builder:** creates a grounded prompt from preferences and selected candidate fields.
7. **LLM client:** sends the request and handles timeouts, retries, and provider errors.
8. **Response validator:** verifies schema, membership, factual fields, and result count.
9. **Presentation layer:** displays recommendations, explanations, caveats, and error states.
10. **Observability layer:** records safe operational metrics for performance and quality monitoring.

## 20. Expected Outcome

The completed application should demonstrate a trustworthy hybrid recommendation workflow. Deterministic processing will provide factual correctness and enforce user constraints, while the LLM will provide comparative reasoning and natural-language explanations. The user should receive a concise list of relevant restaurant choices, understand why each one was recommended, see any important caveats, and remain protected from fabricated or unsupported claims.

The central measure of success is not simply whether the application can generate fluent recommendations. It is whether those recommendations are useful, personalized, verifiably grounded in the source data, and robust when the available information or external AI service is imperfect.
