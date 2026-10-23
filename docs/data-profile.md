# Dataset Discovery Profile

## Status

- Discovery date: 2026-10-15
- Dataset: `ManikaSaini/zomato-restaurant-recommendation`
- Source: <https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation>
- Pinned Git commit: `5738e9eda2fad49ad51c6e0ed26e761d9b947133`
- Source file: `zomato.csv`
- Source file size: approximately 574 MB
- Source SHA-256 published by Hugging Face: `4b0c91c37585310d509873dc399fdf739c7d222fcf7a693e4461b23d25a9d43d`
- Split: `train`
- Rows reported by the dataset viewer: 51,717
- Dataset card: absent at the time of discovery

The full source file was not committed or downloaded during Phase 0 because its large `reviews_list` and `menu_item` values make it 574 MB. Phase 1 must download the pinned revision through a controlled ingestion adapter and verify its SHA-256 before processing.

## Scope Finding

Despite the broader product examples mentioning cities such as Delhi and Bangalore, this dataset is a Bangalore restaurant dataset. The `location` field contains 93 locality-like values, while `listed_in(city)` contains 30 listing areas within Bangalore. The MVP cannot truthfully support arbitrary Indian cities from this source alone.

Phase 1 and Phase 2 should therefore treat Bangalore as the supported city and `location` as the primary locality field unless a second verified dataset is deliberately introduced.

## Source Schema

| Source column | Viewer type/shape | Example | Initial use |
|---|---|---|---|
| `url` | String, length 180-538 | Zomato restaurant URL | Traceability and source-key input |
| `address` | String, length 6-346 | Street address in Bangalore | Display only |
| `name` | String, length 2-159 | `Jalsa` | Restaurant name |
| `online_order` | Two string values | `Yes` | Optional verified attribute |
| `book_table` | Two string values | `No` | Optional verified attribute |
| `rate` | String, 64 observed classes | `4.1/5` | Parse to numeric rating and scale |
| `votes` | Integer, 0-16.8k | `775` | Rating-confidence signal |
| `phone` | Nullable string, length 11-34 | Phone numbers | Excluded from MVP recommendations |
| `location` | String, 93 observed classes | `Banashankari` | Primary locality |
| `rest_type` | String, 93 observed classes | `Casual Dining` | Optional restaurant type |
| `dish_liked` | Nullable string, length 2-134 | `Pasta, Lunch Buffet` | Excluded initially; unstructured evidence candidate |
| `cuisines` | Nullable string, length 3-86 | `North Indian, Mughlai, Chinese` | Normalized cuisine list |
| `approx_cost(for two people)` | String, 70 observed classes | `800` | Parse as INR cost for two |
| `reviews_list` | String, up to about 1.28M characters | Serialized review tuples | Excluded from MVP ingestion payload |
| `menu_item` | String, up to about 24.9k characters | Serialized menu list | Excluded from MVP ingestion payload |
| `listed_in(type)` | String, 7 observed classes | `Buffet` | Optional listing category |
| `listed_in(city)` | String, 30 observed classes | `Banashankari` | Listing area, not a general city field |

## Important Data-Quality Observations

The viewer and sampled rows expose these issues that Phase 1 must measure precisely:

- The `rate` column is a string rather than a number and has many classes, implying unrated/placeholder values in addition to values such as `4.1/5`.
- `approx_cost(for two people)` is a formatted string and must be parsed without losing its “for two people” basis.
- `cuisines`, `dish_liked`, and `phone` are nullable.
- Individual restaurants appear more than once under different listing categories. For example, the sample shows San Churro Cafe in both Buffet and Cafes listings.
- `listed_in(city)` is misleadingly named: observed examples are Bangalore areas, not separate cities.
- Review text is extremely large and may contain unsafe or malformed content. It is outside the initial canonical restaurant model.
- Sampled names and reviews show mojibake/encoding artifacts, so Phase 1 must report encoding quality rather than silently “repairing” uncertain text.
- URLs contain long context parameters and may not be stable enough to serve as the only identity field without normalization.
- Costs appear to be INR amounts for two people. Hidden currency conversion is not allowed.

## Proposed Canonical Mapping

| Canonical field | Source/derivation | Phase 1 rule to confirm |
|---|---|---|
| `source_key` | Normalized URL plus identity fingerprint | Prefer stable URL path; detect collisions |
| `name` | `name` | Required, preserve display text |
| `name_normalized` | `name` | Unicode normalize, trim, collapse whitespace, case-fold |
| `city` | Constant `Bangalore` for this source | Record as a dataset-level assumption |
| `city_normalized` | Constant `bangalore` | Version the mapping |
| `locality` | `location` | Nullable only if source requires it |
| `locality_normalized` | `location` | Normalize conservatively; aliases require approval |
| `address` | `address` | Optional display value |
| `cuisines` | `cuisines` | Split on documented commas, normalize and deduplicate |
| `average_cost_minor` | `approx_cost(for two people)` | Parse INR and multiply rupees by 100 |
| `currency_code` | Dataset assumption | `INR` only when cost parses successfully |
| `cost_basis` | Column semantics | `for_two_people` |
| `rating` | `rate` | Parse numerator; placeholders become unavailable |
| `rating_scale` | `rate` suffix | Expected `5`, validate every parsed row |
| `votes` | `votes` | Non-negative integer or unavailable |
| `attributes.online_order` | `online_order` | Strict Yes/No mapping |
| `attributes.book_table` | `book_table` | Strict Yes/No mapping |
| `attributes.restaurant_types` | `rest_type` | Normalize as a list if supported |
| `attributes.listing_type` | `listed_in(type)` | Preserve only if useful to filtering/display |
| `source_url` | `url` | Preserve for traceability; do not fetch at request time |

## Fields Excluded from the Initial Canonical Model

- `phone`: not required for recommendation and creates unnecessary contact-data handling.
- `reviews_list`: too large and untrusted; using it requires a separate evidence and safety design.
- `menu_item`: large, inconsistently structured, and not needed for explicit MVP requirements.
- `dish_liked`: may be revisited only after its semantics, missingness, and evidence use are evaluated.

Exclusion prevents accidental prompt expansion and unsupported claims. Raw source data may be available to the offline ingestion process but should not be copied into serving tables without a documented decision.

## Phase 1 Profiling Requirements

The full pinned file must be profiled for:

- Exact null, blank, malformed, and distinct counts by relevant column.
- Exact duplicate rows and identity-level duplicates.
- URL-path stability and fingerprint collision rate.
- Rating parse success, placeholder values, range, and scale.
- Cost parse success, range, grouping separators, and unexpected values.
- Cuisine token frequency and delimiter anomalies.
- Location/listing-area relationship.
- Boolean vocabulary for ordering and booking.
- Encoding/mojibake incidence.
- Accepted and rejected row projections under the proposed model.

Quality thresholds must be based on those measurements rather than guessed in advance.

## Phase 0 Fixture

`docs/fixtures/restaurants_phase0.csv` is synthetic and deliberately covers valid, missing, boundary, duplicate-listing, unsafe-text, and malformed cases. It is not a sample of the full copyrighted source file and must not be used to report source statistics.

## Open Decisions for Phase 1

1. Final stable identity rule for duplicate restaurant listings.
2. Whether branches sharing a name remain distinct based on address/URL path.
3. Treatment of mojibake: preserve, reject, or repair only recognized patterns.
4. Whether `rest_type` and listing type enter the canonical optional attributes.
5. Exact minimum quality gates after full-file profiling.
6. Whether the source license/usage terms are sufficient for the intended deployment; the Hugging Face repository currently has no dataset card.

