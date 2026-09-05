# ADR-003: Bedrock Model Abstraction

- **Status:** Accepted
- **Decision date:** 2026-08-26

## Context

Amazon Bedrock is the preferred production model/embedding provider, while CI must run offline and future tasks may require different capabilities. Direct SDK calls in domain/workflow logic would entangle provider identifiers, retries, schemas, telemetry, and tests.

## Decision

Define internal `ModelGateway` and `EmbeddingGateway` ports with task policies, capability declarations, structured outputs, budgets, usage/cost telemetry, and stable error classes. Implement deterministic mock adapters first and Bedrock adapters later. Business logic names tasks/model policies, never Bedrock model IDs.

## Alternatives

- **Direct Bedrock calls:** quickest initially, but creates coupling and credential-dependent tests.
- **Generic third-party LLM abstraction only:** broad integrations but may hide provider features and governance metadata.
- **Self-hosted models:** control and offline operation, with significant evaluation, serving, and security burden.

## Trade-offs and consequences

An abstraction can collapse to a lowest common denominator. Capability negotiation and provider-specific adapter options prevent that while keeping domain code clean. Raw provider responses are minimized and referenced according to retention policy.

## Success criteria

All CI workflows pass with the mock; contract tests apply to every provider; outputs and errors are provider-normalized; model/provider/version, usage, latency, cost, and safety metadata are reconstructable; switching a task policy requires no domain-code change.
