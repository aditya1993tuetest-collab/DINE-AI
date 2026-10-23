# ADR 0006: Limit Initial Dataset Scope to Bangalore

- Status: accepted
- Date: 2026-10-15

## Context

The referenced Hugging Face dataset has 51,717 rows but represents Bangalore restaurants. Its `location` and misleadingly named `listed_in(city)` fields contain Bangalore areas rather than multiple Indian cities.

## Decision

Treat Bangalore as the only supported city for the first dataset-backed release. Use `location` as the primary locality after Phase 1 profiling. Do not imply support for Delhi or other cities without an additional verified data source.

## Consequences

- The MVP remains honest about coverage.
- Product examples and validation must reflect supported locations.
- Multi-city expansion requires a separate data-source decision and normalization review.

## Alternatives

Inferring cities from listing areas or addresses was rejected because it would introduce unsupported assumptions.

