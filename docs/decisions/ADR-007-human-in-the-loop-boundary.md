# ADR-007: Human-in-the-Loop Decision Boundary

- **Status:** Accepted
- **Decision date:** 2026-08-26

## Context

Claims work can affect coverage, payments, fraud handling, legal positions, and customer communication. Model outputs can be unsupported or ambiguous. Human oversight must be an enforceable workflow state, not a disclaimer.

## Decision

The system provides decision support only. It cannot autonomously approve/deny coverage, issue payment, accuse fraud, make legal conclusions, or send consequential external communication. Mandatory, persisted human review occurs for approved trigger categories. Resume requires an authorized reviewer, snapshot/version match, allowed decision, and reason.

## Alternatives

- **Advisory banner only:** easy but does not prevent automated action.
- **Human reviews every output:** safe-looking but costly, causes rubber-stamping, and obscures targeted risk.
- **Model confidence threshold:** opaque and poorly calibrated.

## Trade-offs and consequences

Review queues add latency and operational work. Explicit triggers and support signals concentrate attention while retaining hard boundaries. All domain trigger thresholds are **SYNTHETIC DEMONSTRATION RULES** in this portfolio.

## Success criteria

100% expected escalation on mandatory golden cases; zero consequential completion without current authorized review; no duplicate/stale decisions; reason and evidence completeness; measured reviewer agreement, queue time, return rate, and false escalation.
