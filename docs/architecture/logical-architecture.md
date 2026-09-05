# Logical Architecture

## Context and boundaries

The platform separates reusable capabilities from the residential-property claims module. The browser is untrusted, APIs enforce identity and authorization, domain services own business invariants, LangGraph coordinates decision-support steps, and provider adapters isolate infrastructure. PostgreSQL is authoritative; search indexes, caches, and generated views are rebuildable derivatives.

See [complete platform diagram](../diagrams/01-platform-architecture.mmd) and [request flow](../diagrams/02-employee-request-flow.mmd).

## Components and decisions

| Component | Business purpose | Technical purpose | Alternatives | Selection and trade-offs | Measurable success |
|---|---|---|---|---|---|
| Vue employee app | Make complex evidence review usable | Accessible role-aware SPA, status streaming | Server-rendered UI, Streamlit | Vue gives strong component/state control; adds frontend build discipline | WCAG checks, task completion, UI error rate |
| FastAPI application | Stable employee and integration boundary | REST/OpenAPI, validation, authorization, commands | Django, Flask, GraphQL | Typed async-friendly boundary; team must design domain layer rather than place logic in routes | Contract tests, p95, error rate |
| Claims domain | Preserve claim invariants | Entities, value objects, commands, policies | CRUD-centric services | Domain separation prevents orchestration/framework coupling; adds modeling work | Invariant tests, change isolation |
| LangGraph workflow | Coordinate reviewable analysis | Persisted state, explicit nodes, conditional edges, interrupts | Custom state machine, Strands, Step Functions | Explicit and testable AI flow; framework dependency is isolated behind workflow ports | Completion, resume correctness, node/tool accuracy |
| Retrieval service | Find governing evidence | Normalize queries, filter, fuse, rerank, cite | Direct vector DB calls | One contract enables benchmarking and backend replacement; abstraction must not hide backend capabilities | recall@k, nDCG@k, latency, citation validity |
| Rules service | Apply stable thresholds | Versioned pure rules and result objects | LLM-only reasoning, external rule engine | Code/data rules are reproducible; complex authoring may later justify a rules engine | deterministic pass rate, coverage, false escalation |
| Support Assessment | Communicate support and risk | Component signals plus escalation policy | LLM confidence, single score | Explainable and actionable; more UI/state complexity | escalation recall, calibration by category, reviewer agreement |
| Review service | Keep humans in control | Queue, assignment, decision, optimistic locking, resume authorization | Email/manual tickets | Durable in-product review; requires queue operations and separation of duties | time-to-review, stale-decision prevention, duplicate rate |
| Model/embedding gateways | Avoid provider coupling | Typed request/response, budgets, retries, telemetry | Direct Bedrock SDK use | Testable mock and provider portability; lowest-common-denominator risk is handled by capability declarations | schema validity, provider parity, cost/latency |
| Audit/evaluation services | Reconstruct and improve behavior | Append-only events, benchmark execution, comparisons | Application logs only | Purpose-built records support governance; storage/retention cost | trace completeness, reproducibility, regression detection |

## Service modularity

The initial deployment is a **modular monolith plus worker**, not premature microservices. Packages communicate through explicit ports and schemas but deploy as an API container and worker container. This preserves transactions and local simplicity. A module may become a service when scaling, security isolation, ownership, or release cadence is demonstrated—not merely anticipated.

### Reusable platform modules

Identity/access, document processing, knowledge catalog, retrieval, model gateway, workflow runtime, review, audit, evaluation, feedback, and telemetry.

### Claims-specific modules

Claim aggregates, residential property document taxonomy, extracted-fact schema, synthetic rules, issue types, claims graph nodes, and claims workspace views.

## Execution patterns

- Synchronous reads and command acceptance use REST.
- Document ingestion and claims analysis are asynchronous, idempotent jobs.
- Transactional outbox rows are committed with domain state, then published to the queue/event bus.
- UI progress uses server-sent events with cursor-based reconnect; polling is a fallback.
- Provider adapters have explicit timeouts, retries, circuit-breaker signals, and capability metadata.
- Generated artifacts reference immutable input snapshots; new evidence makes earlier artifacts stale rather than silently rewriting them.

## Invariants

1. An authorized actor and tenant context are required before resource lookup.
2. Original documents cannot be modified after acceptance.
3. No index result can bypass source-document authorization.
4. A governing policy citation must pass identity, edition, endorsement, and effective-date validation.
5. A workflow cannot resume without a valid review decision tied to the interrupted snapshot.
6. Consequential actions are proposals until an authorized human acts outside or through an approved integration boundary.
7. Audit failure blocks consequential state changes; nonconsequential telemetry failure degrades visibly without corrupting domain state.

## Dependency direction

Delivery and infrastructure adapters depend on application ports; application services depend on domain types; the domain depends on neither FastAPI, LangGraph, AWS, nor database libraries. Workflow nodes call application ports and return typed state deltas. This makes deterministic unit tests and provider substitutions possible.
