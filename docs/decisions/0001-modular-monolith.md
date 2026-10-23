# ADR 0001: Start with a Modular Monolith

- Status: accepted
- Date: 2026-10-15

## Context

The system requires ingestion, filtering, ranking, LLM orchestration, validation, and a web API, but initial scale and team boundaries do not justify independently deployed services.

## Decision

Build one FastAPI backend with explicit domain, application, infrastructure, ingestion, and transport modules. Run ingestion as a separate command/container using the same internal packages.

## Consequences

- Local development and deployment remain simple.
- Module boundaries must be enforced in code and tests.
- Ingestion and LLM orchestration can be extracted later if measured scale requires it.

## Alternatives

Microservices were rejected for the MVP because they add network, deployment, consistency, and observability overhead without demonstrated need.

