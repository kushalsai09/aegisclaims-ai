# ADR-011: Terraform and ECS/Fargate Production Foundation

**Status:** Accepted

## Decision

Use Terraform with a pinned AWS provider to define an initial multi-AZ
ECS/Fargate deployment for separate web, API, and worker containers behind an
ALB, with RDS PostgreSQL, ElastiCache Valkey, S3, ECR, Secrets Manager
references, private networking, CloudWatch, and OpenTelemetry boundaries.

## Rationale and consequences

Terraform makes the cloud contract reviewable without coupling it to application
language. Fargate matches the existing containers and long-running API/worker
shape without operating Kubernetes. It costs more at low idle utilization than
scale-to-zero functions and requires measured right-sizing. The checked module
is a reference foundation, not evidence of an AWS deployment; account-specific
state, DNS, certificates, WAF, secrets, alert routes, and policy review remain
deployment prerequisites.

