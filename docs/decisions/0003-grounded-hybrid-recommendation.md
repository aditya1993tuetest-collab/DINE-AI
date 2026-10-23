# ADR 0003: Filter Deterministically and Ground LLM Output

- Status: accepted
- Date: 2026-10-15

## Context

An unconstrained language model may violate numeric filters, invent restaurants, or alter ratings and costs.

## Decision

Application code and database queries enforce all hard constraints. The LLM receives only a bounded eligible candidate list and returns restaurant IDs plus explanations. The backend validates membership and rehydrates all factual fields from trusted records.

## Consequences

- Hard constraints and facts are testable independently of the model.
- The LLM cannot be used as the factual source of restaurant data.
- Provider failure can fall back to deterministic ordering and template explanations.

## Alternatives

Allowing the model to search or generate candidates was rejected because it violates grounding and repeatability requirements.

