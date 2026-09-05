# AWS Production Architecture

## Recommended deployment

The service table below describes the broader target architecture. The exact
Phase 7 checked foundation is narrower: ALB, ECS/Fargate, RDS PostgreSQL,
ElastiCache Valkey, S3, ECR, Secrets Manager references, CloudWatch, and a
private OTLP boundary. SQS, EventBridge, WAF, custom KMS, and Cognito are not
implemented by the current Terraform. See
[Phase 7 production readiness](phase7-production-readiness.md) for the
authoritative implemented-versus-future boundary.

The initial AWS topology uses one account per environment where practical, private subnets across multiple availability zones, an internet-facing ALB for the Vue/API edge, ECS/Fargate for API and worker containers, S3 for documents and static assets, Aurora PostgreSQL-compatible or RDS PostgreSQL with pgvector, SQS for jobs and dead-letter queues, EventBridge for low-coupling domain notifications, ECR for images, and CloudWatch/OpenTelemetry for telemetry. Terraform defines all resources.

See [AWS deployment diagram](../diagrams/07-aws-deployment.mmd).

## Service choices

| AWS service | Purpose | Alternatives considered | Reason and trade-offs | Adoption criterion |
|---|---|---|---|---|
| ALB | Route HTTPS to ECS and support streaming | API Gateway | Simple container ingress and SSE; API Gateway is preferable if API-product controls outweigh streaming/cost considerations | Load, auth, WAF, and streaming tests |
| ECS/Fargate | Run API and long/variable workers | Lambda, EKS, AgentCore Runtime | Container portability and no cluster operation; less scale-to-zero efficiency than Lambda | p95, task utilization, deployment recovery |
| Lambda | Short S3/EventBridge adapters only | Fargate worker | Efficient event glue; duration/runtime limits make it a poor default workflow host | Handler duration and failure profile fit |
| S3 | Immutable documents, derived artifacts, exports | Database blobs, EFS | Durable versioned object storage; consistency between metadata and object events needs reconciliation | Integrity, lifecycle, restore tests |
| Aurora/RDS PostgreSQL | Authoritative transactional and vector store | DynamoDB, OpenSearch-only | Relational integrity plus pgvector/FTS; vector scale may eventually require a separate engine | Query/retrieval benchmark and operations cost |
| SQS | At-least-once work delivery and DLQs | Kafka/MSK, EventBridge only | Managed backpressure and retries; consumers must be idempotent | Duplicate/retry/poison-message tests |
| EventBridge | Publish low-volume domain events | SNS, Kafka | Routing without tight coupling; not a workflow state store | Event delivery and archive/replay needs |
| Bedrock | Managed generation and embeddings | Direct model APIs, self-hosting | AWS IAM/governance and model choice; availability, quota, regional, and model behavior differences require gateway abstraction | Model evaluation, quota, cost, region approval |
| Cognito/federation | OIDC identity | Custom identity | Standards boundary with AWS integration; enterprise deployments may federate an existing IdP | Claims/role mapping and lifecycle tests |
| KMS/Secrets Manager | Keys and secrets | Static environment values | Rotation and access control; adds policy/configuration complexity | Rotation and access-denial tests |
| CloudWatch | Default AWS logs/metrics/alarms | Managed third-party observability | Native integration; OpenTelemetry preserves portability | Trace completeness and alert usefulness |

## Optional services

- **OpenSearch:** adopt only when hybrid retrieval benchmarks, corpus size, filtering, or operational separation materially outperform PostgreSQL at acceptable cost.
- **Textract:** adopt for scanned/layout-heavy documents if open-source extraction fails measured accuracy and latency requirements. Text-native synthetic fixtures do not justify it alone.
- **AgentCore:** optional isolated spike for runtime isolation, identity, gateway-governed tools, and agent telemetry. The main graph cannot depend on it; see ADR-005.
- **SageMaker:** appropriate for a validated custom classifier, prioritization model, anomaly detector, or reranker whose offline and online performance beats simpler approaches; see ADR-006.

## Network and identity

- ALB is the only public application ingress; WAF, TLS, security headers, and rate controls apply at the edge.
- ECS tasks, database, and internal endpoints reside in private subnets. Database security groups accept only authorized application task groups.
- Prefer VPC endpoints for S3, ECR, CloudWatch, Secrets Manager, KMS, SQS, and supported Bedrock access to reduce public egress.
- Separate API and worker task roles. Neither receives broad wildcard permissions. Human identity is propagated as verified claims; workload identity remains distinct.
- S3 access is through service authorization or short-lived scoped URLs after document authorization—not public buckets.

## Data protection and resilience

- KMS keys are separated by data class/environment; key policies are reviewed and rotation is enabled where supported.
- S3 versioning, block-public-access, lifecycle rules, checksum validation, and access logging are enabled.
- Database encryption, automated backups, point-in-time recovery, multi-AZ deployment, and restore exercises support the initial RPO/RTO objectives.
- Queue redrive policies, DLQs, alarms, idempotency keys, and reconciliation jobs address at-least-once processing.
- Infrastructure and application deploy independently through immutable artifacts and backward-compatible migrations.

## Environment strategy

Local, CI, development, staging, and production use identical contracts but different adapters/configuration. Production data never flows into lower environments. Model access and internet egress are disabled by default in CI. Terraform modules are shared; environment state, accounts, keys, secrets, domains, budgets, and approvals are separate.

## Capacity and cost controls

Fargate tasks use measured CPU/memory requests and autoscaling on queue depth, latency, and utilization. Bedrock concurrency, token budgets, and request caps are enforced in the application gateway. Nonproduction schedules scale down workers. S3 lifecycle tiers derived artifacts. Budgets and anomaly alarms are mandatory before enabling paid model traffic.

## Primary references

- [Amazon ECS on AWS Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [Amazon Bedrock security and privacy](https://docs.aws.amazon.com/bedrock/latest/userguide/security.html)
- [Amazon Aurora PostgreSQL and pgvector](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.VectorDB.html)
- [Amazon SQS delivery model](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html)
- [Amazon Bedrock AgentCore developer guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html)
