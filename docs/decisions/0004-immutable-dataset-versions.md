# ADR 0004: Publish Immutable Dataset Versions Atomically

- Status: accepted
- Date: 2026-10-15

## Context

In-place dataset updates can expose partially processed data, invalidate cached results unpredictably, and make evaluations irreproducible.

## Decision

Each ingestion creates a new immutable dataset version in staging. A version becomes active only after schema, data-quality, and database checks pass. Activation is transactional, and the previous version is retained for rollback.

## Consequences

- Requests, caches, audits, and evaluations can reference exact data.
- Publication needs additional storage and lifecycle management.
- Activation concurrency must be serialized.

## Alternatives

Updating a single serving table in place was rejected because it lacks atomic rollback and traceability.

