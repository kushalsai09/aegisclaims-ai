# ADR-008: Support Assessment versus Naive Confidence

- **Status:** Accepted
- **Decision date:** 2026-08-26

## Context

An LLM-generated “96% confidence” has no stable probabilistic meaning and conceals distinct failure modes. Employees need to know what is supported, missing, contradictory, invalid, or risky.

## Decision

Create a structured Support Assessment from evidence coverage, retrieval results, required-field completeness, citation validity, contradiction state, rule status, policy-version validity, evaluation warnings, risk category, and escalation reason codes. Do not expose an aggregate probability unless future empirical calibration supports a clearly defined outcome.

## Alternatives

- **LLM self-confidence:** fluent but ungrounded.
- **Weighted single score:** compact but hides compensating failures and arbitrary weights.
- **No support indicator:** forces users to infer risk from scattered panels.

## Trade-offs and consequences

Multiple signals require more data contracts and UI design. They are actionable and auditable. The LLM may phrase a concise rationale but cannot calculate or override signals.

## Success criteria

Every component is reproducible from stored inputs; reviewers can identify escalation cause; missing/failed critical signals cannot be masked by good unrelated signals; category-level escalation performance and reviewer agreement are measured.
