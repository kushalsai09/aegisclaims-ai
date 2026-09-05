# ADR-001: LangGraph versus Strands

- **Status:** Accepted
- **Decision date:** 2026-08-26

## Context

The claims workflow needs explicit state, deterministic routing, durable checkpoints, bounded tools, and human interrupts. AWS-oriented Strands offers a concise model-driven agent/tool abstraction, but using two orchestration frameworks would increase runtime and evaluation complexity.

## Decision

Use LangGraph as the primary orchestration framework behind application ports. Do not place claims rules or authorization inside framework-specific nodes. Document Strands and later build an optional isolated spike using the same model/tool contracts; do not ship both in the main runtime.

## Alternatives

- **Strands primary:** simpler model-directed loop and Bedrock affinity, but less appropriate as the reference control plane for this explicitly staged workflow.
- **Custom state machine:** maximum control, but recreates checkpoint/interrupt mechanics.
- **AWS Step Functions:** strong infrastructure orchestration, but duplicates application-level AI state and harms local parity.

## Trade-offs and consequences

LangGraph adds a dependency and requires state/version discipline. In exchange, workflow paths and interrupts are explicit and testable. Framework containment preserves a future change. Strands tool loading or execution must never bypass the platform tool registry/security model in a spike.

## Success criteria

Deterministic graph path tests, restart-safe checkpoints, idempotent replay, stale-review rejection, zero unauthorized tool calls, and an isolated Strands comparison report covering quality, control, latency, cost, and operational complexity.

## References

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [Strands Agents overview](https://strandsagents.com/docs/user-guide/quickstart/overview/)
- [Strands tool security considerations](https://strandsagents.com/docs/user-guide/concepts/tools/)
