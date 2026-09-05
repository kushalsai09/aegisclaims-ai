# Architecture Decision Records

All ADRs are **Accepted** for the documentation baseline unless superseded. Significant changes add a new ADR; accepted records are not silently rewritten to hide prior rationale.

| ADR | Decision |
|---|---|
| [ADR-001](ADR-001-langgraph-vs-strands.md) | LangGraph primary; Strands isolated comparison |
| [ADR-002](ADR-002-postgresql-pgvector-vs-opensearch.md) | PostgreSQL hybrid retrieval first |
| [ADR-003](ADR-003-bedrock-model-abstraction.md) | Internal model/embedding gateways |
| [ADR-004](ADR-004-fargate-vs-lambda.md) | Fargate API/workers; Lambda event glue |
| [ADR-005](ADR-005-agentcore-adoption.md) | Optional AgentCore spike |
| [ADR-006](ADR-006-sagemaker-adoption.md) | Evidence-driven SageMaker adoption |
| [ADR-007](ADR-007-human-in-the-loop-boundary.md) | Human authority for consequential/unsupported work |
| [ADR-008](ADR-008-support-assessment.md) | Explainable Support Assessment, no naive confidence |
| [ADR-009](ADR-009-deterministic-rules-vs-llm.md) | Deterministic rules where sufficient |
| [ADR-010](ADR-010-vue-vs-rapid-ui.md) | Vue primary employee application |
| [ADR-011](ADR-011-terraform-ecs-foundation.md) | Terraform ECS/Fargate production foundation |
| [ADR-012](ADR-012-redis-operational-boundary.md) | Redis queue and distributed rate-limit boundary |
| [ADR-013](ADR-013-oidc-internal-rbac.md) | OIDC identity with internal RBAC authority |
