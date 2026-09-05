# Phase 7 Production-Readiness Architecture

## Implemented baseline

Phase 7 keeps the modular monolith and separates three deployable processes:
the Vue/Nginx web edge, FastAPI API, and Redis-backed worker. PostgreSQL remains
authoritative for identity mappings, sessions, claims, workflow state, review
state, model invocation records, and audit events. S3-compatible object storage
owns document bytes. Redis is non-authoritative and provides the work queue and
shared fixed-window rate limits.

The checked Terraform foundation deploys the three containers on ECS/Fargate
across two availability zones behind a TLS ALB. It creates private task
subnets, RDS PostgreSQL Multi-AZ, encrypted Multi-AZ ElastiCache for Valkey,
versioned/block-public S3 storage, immutable ECR repositories, VPC endpoints,
CloudWatch logs and alarms, and ECS target-tracking autoscaling. Runtime secret
values are referenced from an existing Secrets Manager JSON secret; Terraform
does not store those values.

This foundation has been formatted and statically validated. It has not been
planned or applied against an AWS account, so no deployed-cloud or live-service
claim is made. See [implemented deployment](../diagrams/13-phase7-aws-foundation.mmd).

## Identity and authorization

Production configuration permits OIDC only. The application implements
authorization-code flow with PKCE, discovery issuer matching, HTTPS endpoint
validation, signed ID-token validation, audience/issuer/expiry/nonce checks,
hashed state, a browser-binding cookie, a ten-minute transaction, and one-time
consumption. An external subject must already map to an active user in the
configured internal tenant. Provider role/group claims do not grant application
roles; database RBAC remains authoritative. Local credentials remain available
only in local/test mode.

## Configuration and secrets

Production-like startup rejects wildcard CORS or hosts, HTTP public URLs,
interactive API documentation, SQLite, local authentication, memory storage,
memory queues, memory rate limiting, deterministic model selection, incomplete
OIDC settings, and static AWS S3 credentials. ECS uses task roles for S3 and
Bedrock. Only database URL, TLS Redis URL, and OIDC client secret are injected
from Secrets Manager.

## Availability and scaling

Liveness proves the process can answer. Readiness separately verifies database,
object storage, and queue and returns a sanitized 503 when any is unavailable.
ALB routing uses readiness; container health uses liveness. API, web, and worker
services start with two tasks, deployment circuit breakers, and CPU target
tracking. Application retry counts are bounded; the worker handles dependency
loss, OS termination, and item failures without exiting or retrying forever.

## Data and query boundaries

Claims and review queues use explicit limit/offset bounds (maximum 200), bulk
load related state, and count directly for dashboards. Phase 7 adds composite
indexes for the highest-frequency tenant-scoped claim, assignment, document,
workflow, and review access paths. Deep offset pagination is capped; cursor
pagination is the next optimization if measured volume justifies an API change.

## Explicitly not implemented

- No AWS account, DNS, certificate, secret, RDS, ECS, S3, Valkey, or Bedrock
  resource was created by this phase.
- WAF, cross-region recovery, custom KMS keys, SQS/DLQ, EventBridge, CloudFront,
  and zero-downtime schema orchestration are future production extensions.
- Redis queue delivery is the implemented Phase 7 worker topology; it is not
  represented as SQS or a durable transactional outbox.
- Live Bedrock invocation remains conditional on approved credentials, region,
  model access, and quota. Deterministic local output is never called live.

