# ADR-005: AgentCore Adoption Strategy

- **Status:** Accepted
- **Decision date:** 2026-08-26

## Context

Amazon Bedrock AgentCore can provide agent runtime isolation and modular identity, gateway, memory, and observability capabilities. The core platform must remain locally runnable and not depend on a rapidly evolving optional managed layer.

## Decision

Preserve an integration boundary and create a later isolated AWS spike. The main application, domain, tool contracts, and LangGraph workflow do not depend on AgentCore. The spike evaluates Runtime hosting and Gateway/Identity/observability only where they solve a measured problem. AgentCore Memory is not a default replacement for authoritative claim/workflow state.

## Alternatives

- **Adopt immediately:** showcases managed capabilities but adds cost, change risk, duplicated governance, and reduced local parity before requirements are proven.
- **Reject permanently:** avoids complexity but ignores potentially valuable isolation and tool governance.
- **Replace LangGraph:** conflates hosting/governance with workflow logic.

## Trade-offs and consequences

The optional approach delays hands-on production integration but keeps architecture defensible. The spike gets its own Terraform module, budget, threat model, benchmarks, and deletion path.

## Success criteria

Compare deployment effort, isolation, auth/tool-policy enforcement, trace completeness, latency, availability, cost, local/staging parity, portability, and operational ownership. Adoption requires a material advantage and no weakening of application authorization, audit, checkpoint, or evaluation contracts.

## References

- [AgentCore Runtime versus agent harness](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness-vs-runtime.html)
- [AgentCore Gateway concepts](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-core-concepts.html)
- [AgentCore observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-telemetry.html)
