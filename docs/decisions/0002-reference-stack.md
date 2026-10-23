# ADR 0002: Adopt the Initial Reference Stack

- Status: accepted
- Date: 2026-10-15

## Context

The project needs typed HTTP contracts, strong data tooling, relational filtering, a modern accessible web client, and reproducible local environments.

## Decision

Use Python 3.12+ with FastAPI and Pydantic for the backend, React with TypeScript and Vite for the web app, PostgreSQL as primary storage, Redis for shared cache/rate limits when introduced, Pytest and Vitest for tests, and Docker Compose for the full local topology.

## Consequences

- Python data libraries can be used during ingestion.
- OpenAPI provides a typed boundary for the web client.
- PostgreSQL supports deterministic filtering and transactional dataset activation.
- Docker is optional for basic Phase 0 checks but required to validate the complete local stack.

## Alternatives

Node-only backend and server-rendered frameworks remain viable but provide no clear advantage for the planned Python ingestion workflow.

