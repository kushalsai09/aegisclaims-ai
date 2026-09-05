# Local and AWS Deployment

## Local development

Docker Compose provides PostgreSQL with pgvector, MinIO, Redis, an
OpenTelemetry Collector, Jaeger, the FastAPI service, Redis-backed worker, and
the Nginx-served Vue application. Start the complete local stack from the
repository root with:

```bash
cp .env.example .env
docker compose -f infrastructure/docker/compose.yaml up -d --build
./scripts/wait-for-stack.sh
```

The API container applies migrations and runs the idempotent synthetic seed
before serving traffic. `.env.example` is the Compose configuration;
`.env.host.example` is the separate SQLite/filesystem/in-memory configuration
for running API and Vite directly on the host.

Default local mode uses:

- deterministic model and embedding providers;
- Redis-backed execution in Compose and a deterministic in-memory queue for
  unit/host paths;
- MinIO through the object-store interface;
- synthetic seed data only;
- a clearly marked development identity provider/stub, disabled in nonlocal environments.

The documented bootstrap initializes schema, verifies and seeds the fictional
tenant/users/documents, and can be followed by the existing smoke tests. Local
configuration uses checked-in nonsecret defaults plus the ignored `.env`
runtime copy. No paid model or external provider credentials are required.

## AWS topology

The Phase 7 Terraform reference defines the VPC/subnets/NAT/endpoints,
security groups, TLS ALB, ECS cluster/services/tasks, ECR, private versioned S3,
RDS PostgreSQL Multi-AZ, ElastiCache Valkey Multi-AZ, least-privilege task roles,
runtime Secrets Manager references, CloudWatch logs/alarms, autoscaling, and
optional Route 53 alias. It does not create WAF, SQS/DLQ, EventBridge, budgets,
custom KMS keys, Cognito, the runtime secret value, remote Terraform state, or
the OTLP collector. Those are explicit environment prerequisites/extensions,
not silently implied deployed services.

## Configuration

Settings are typed, environment-specific, and fail fast. Nonsecret configuration includes adapter selection, endpoints, feature flags, task model policies, limits, and telemetry. Secrets are injected at runtime by reference. Environment variables never select an unsafe local auth/mock provider in staging or production; startup policy rejects that configuration.

## Release and migration

- Immutable container digest and release manifest.
- Separate database migration task with advisory lock and backup/restore readiness.
- Rolling or blue/green ECS deployment with readiness gates and connection draining.
- Queue consumers use backward-compatible event schemas and can be paused/drained.
- New index versions build alongside active versions and switch atomically after evaluation.
- Prompt/model/retrieval rollouts use versioned feature configuration and canary cohorts where appropriate.

## Operational readiness

Before production-like enablement: capacity test, failure injection, restore exercise, credential/key rotation test, DLQ redrive exercise, dependency quota validation, security scan, threat-model review, alert routing test, runbook review, and documented on-call/owner map.

## Optional integration spikes

AgentCore, Textract, OpenSearch, and SageMaker deploy into isolated Terraform modules/stacks and use existing contracts. A spike must define hypothesis, benchmark, cost cap, security review, exit criteria, and removal procedure. No spike becomes a transitive requirement of local development or the main runtime.

## Disaster recovery

The initial architecture is single-region with multi-AZ resilience. RPO 15 minutes and RTO 4 hours are objectives pending restore validation. Cross-region recovery is not claimed; it requires approved business requirements, replicated data/key design, provider/model availability analysis, and tested failover.
