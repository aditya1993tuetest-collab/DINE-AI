# ADR 0005: Keep the LLM Provider Behind a Typed Adapter

- Status: accepted
- Date: 2026-10-15

## Context

The first model provider has not been selected, and provider SDK types or error semantics should not enter domain logic.

## Decision

Define an asynchronous internal ranking protocol with typed request and result models. Provider adapters own authentication, SDK translation, deadlines, retryable error classification, request identifiers, and token metadata.

## Consequences

- A deterministic fake adapter can support local development and CI.
- Models and providers can be evaluated or replaced without changing filtering.
- Provider-specific structured-output features must map to the common contract.

## Alternatives

Calling a provider SDK directly from route handlers was rejected because it couples transport, business policy, and vendor behavior.

