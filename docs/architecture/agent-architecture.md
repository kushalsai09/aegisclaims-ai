# LangGraph and Agent Architecture

## Phase 4 implementation

Phase 4 implements LangGraph only as the typed, in-process node router. Application-owned PostgreSQL tables provide durable checkpoints, transition history, review artifacts, and reviewer actions. This is a deliberate containment choice: native framework checkpoint persistence would duplicate authoritative lifecycle data outside the existing tenant and claim authorization path. The implementation has no LLM agent and exposes no tools to model reasoning.

## Design position

The claims workflow is a bounded state machine with selectively agentic nodes, not an autonomous general-purpose agent. LangGraph coordinates durable execution, typed state, conditional transitions, retries, and human interrupts. Authorization and risk decisions remain outside model discretion.

See [claims workflow](../diagrams/05-langgraph-workflow.mmd) and [human review workflow](../diagrams/06-human-review.mmd).

## State model

`ClaimsWorkflowState` contains identifiers rather than document bodies: tenant, claim, actor/context reference, workflow/run/version, immutable input snapshot, current stage, authorized evidence IDs, extracted fact IDs, issue IDs, rule-result IDs, retrieval run IDs, artifact IDs, Support Assessment, review task/decision references, error/retry state, and trace correlation ID.

Large payloads live in authoritative stores. State fields are schema-versioned, checkpointed after material transitions, encrypted at rest, and migrated explicitly.

## Nodes

1. **Authorize and snapshot** — rechecks action permission and freezes claim/document/policy versions.
2. **Assemble case** — loads structured records and ingestion readiness.
3. **Assess prerequisites** — deterministic completeness and policy-identity checks.
4. **Retrieve evidence** — runs typed hybrid searches through the retrieval service.
5. **Extract/synthesize facts** — loads existing extractions or invokes a schema-bounded model task.
6. **Detect issues** — deterministic comparisons plus bounded semantic contradiction analysis.
7. **Evaluate rules** — executes versioned **SYNTHETIC DEMONSTRATION RULES**.
8. **Draft artifact** — creates cited summary and proposed next actions, subject to output policy.
9. **Validate artifact** — schema, citation, prohibited-action, support, and freshness checks.
10. **Build Support Assessment** — aggregates measurable signals and reason codes.
11. **Route** — deterministic complete, abstain, retry, fail, or interrupt decision.
12. **Human review interrupt** — persists a unique task and waits without holding a process.
13. **Apply review decision** — validates reviewer authorization and snapshot concurrency.
14. **Finalize** — writes immutable artifact version, status, audit, and outcome events.

## Tool model

Tools are typed application operations such as `retrieve_evidence`, `get_claim_snapshot`, `evaluate_rules`, `validate_citations`, and `create_review_task`. Each tool declares input/output schema, permitted graph nodes, required actor/workload permissions, read/write effect, timeout, retry behavior, audit event, and data classification.

Models cannot discover arbitrary network, shell, database, or filesystem tools. A model-proposed call is only a request: the orchestrator checks graph allowlist, schema, authorization, budget, and current state. Write-capable or consequential tools are not exposed to the model in the reference workflow.

## Routing and retries

Routing uses deterministic predicates over typed results. LLM text never names the next node directly. Retryable infrastructure errors use bounded attempts and checkpointed backoff scheduling; validation and authorization failures are non-retryable. Node idempotency keys combine run, node, input snapshot, and attempt semantics.

## Human interrupt

Mandatory triggers include critical missing evidence, material contradiction, unsupported answer, policy/version ambiguity, failed blocking rule, high-risk category, prohibited or consequential proposal, security concern, and configured evaluation failure. All domain thresholds are **SYNTHETIC DEMONSTRATION RULES**.

The interrupt stores the reason codes and evidence/artifact snapshot. Resume requires an open task, authorized reviewer, allowed decision, matching version, and recorded reason. New evidence invalidates the task and starts re-analysis rather than applying a stale decision.

## Memory

Workflow state is case-scoped operational memory. The platform does not use uncontrolled cross-claim conversational memory. Employee preferences, if ever added, require a separate consent, retention, and authorization design. Retrieval is the source for durable knowledge, not accumulated chat history.

## Framework containment

Graph construction and checkpoint adapters live in the workflow package. Domain services do not import LangGraph. This allows graph unit testing, state migration, an optional Strands spike, or a future runtime change without rewriting claim rules and evidence contracts.

## Primary references

- [LangGraph overview and durable human-in-the-loop capabilities](https://docs.langchain.com/oss/python/langgraph/overview)
- [Strands Agents overview](https://strandsagents.com/docs/user-guide/quickstart/overview/)
