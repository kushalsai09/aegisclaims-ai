# Enterprise AI Insurance Operations Platform

Status: Phase 7 production-readiness controls and a validated Terraform reference foundation are implemented. No AWS deployment or live Bedrock invocation is claimed.

This documentation describes a fictional, single-organization enterprise AI platform whose first reference workflow is the Residential Property Claims Intelligence Copilot. All people, policies, claims, documents, and business rules are synthetic. Nothing here represents a real insurer's systems, rules, data, or legal obligations.

## Decision boundary

The platform provides evidence-grounded decision support. It does not approve or deny coverage, issue payments, accuse a person of fraud, or make legal conclusions. Consequential actions require an authorized employee. Any rule labelled **SYNTHETIC DEMONSTRATION RULE** exists only to exercise the architecture and tests.

## Canonical architecture baseline

- Vue 3 and TypeScript employee application; FastAPI and Pydantic backend.
- LangGraph owns claims workflow state and human-review interrupts.
- PostgreSQL is the system of record; pgvector and PostgreSQL full-text search provide the initial hybrid retrieval implementation.
- Original and derived documents live in S3-compatible object storage.
- Asynchronous work uses a queue abstraction: memory in unit tests and Redis/Valkey in Compose and the Phase 7 AWS foundation. SQS/DLQ is a future durability extension.
- Models and embeddings are accessed through internal gateways; Amazon Bedrock is the preferred AWS provider and a deterministic mock provider is mandatory.
- OpenTelemetry is the telemetry contract. CloudWatch is the default AWS backend.
- The checked AWS reference uses Terraform, ECS/Fargate, ALB, RDS PostgreSQL, ElastiCache Valkey, S3, ECR, Secrets Manager references, enterprise OIDC, CloudWatch, and a private OpenTelemetry collector boundary.
- OpenSearch, Textract, AgentCore, and SageMaker are optional, benchmark- or requirement-driven additions.

## Document map

- [Product](product/product-overview.md)
- [Logical architecture](architecture/logical-architecture.md)
- [Phase 4 controlled workflows](architecture/phase4-controlled-workflows.md)
- [Phase 5 governed model assistance](architecture/phase5-model-assistance.md)
- [Phase 6 authentication and provider boundary](architecture/phase6-authentication-and-provider.md)
- [Phase 6 product experience](architecture/phase6-production-experience.md)
- [Phase 7 production readiness](architecture/phase7-production-readiness.md)
- [Security](security/security-architecture.md)
- [Evaluation](evaluation/evaluation-strategy.md)
- [Phase 4 workflow evaluation](evaluation/phase4-workflows.md)
- [Phase 5 model-assistance evaluation](evaluation/phase5-model-assistance.md)
- [Phase 6 adversarial model evaluation](evaluation/phase6-adversarial-model.md)
- [Operations](operations/observability.md)
- [Phase 4 workflow operations](operations/phase4-workflows.md)
- [Phase 5 model-assistance operations](operations/phase5-model-assistance.md)
- [Phase 6 operations](operations/phase6-production-experience.md)
- [Phase 7 runbook](operations/phase7-runbook.md)
- [Architecture decisions](decisions/README.md)
- [Diagrams](diagrams/README.md)
- [Implementation plan](IMPLEMENTATION_PLAN.md)

## Normative language

“Must” is an acceptance requirement, “should” is the preferred design with a documented exception path, and “may” is optional. UTC timestamps, UUID identifiers, explicit `tenant_id` boundaries, immutable versions, and append-only audit events are used throughout.
