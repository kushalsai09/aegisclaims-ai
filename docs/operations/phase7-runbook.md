# Phase 7 Operations and Recovery Runbook

## Service indicators

- `GET /health/live`: process lifecycle only.
- `GET /health/ready`: database, object storage, and queue eligibility.
- `/metrics`: bounded route-template latency/counts, authentication outcomes,
  rate-limit rejections, worker failures, workflow/retrieval/model metrics, and
  provider/model token counters when the provider returns billing tokens.
- Structured logs and OpenTelemetry include safe correlation IDs. Claim text,
  passwords, tokens, OIDC codes, and secret values must not be telemetry labels.

The AWS foundation sends container logs to CloudWatch, enables Container
Insights, auto-scales services on CPU, and defines ALB 5xx, RDS free-storage,
and Valkey CPU alarms. `alarm_action_arns` must point to approved incident
routes before production. A private OTLP/HTTP collector endpoint is required.

## Release sequence

1. Build and scan immutable API, worker, and OIDC-mode web images.
2. Back up the database and confirm restore tooling; review the migration.
3. Run backward-compatible migration `20260826_0007` as a controlled one-off
   task. Do not let every API replica race schema changes in production.
4. Deploy worker and API tasks with deployment circuit breakers, then web.
5. Require healthy target groups, smoke tests, logs, metrics, and OIDC sign-in.
6. Roll back the task definition on failure. Database downgrade requires an
   explicit data-compatibility decision; do not blindly downgrade after writes.

The reference Compose entrypoint migrates and seeds synthetic data for local
development only. That bootstrap is not the production release procedure.

## Dependency incidents

- **PostgreSQL:** readiness fails; stop state-changing traffic, inspect RDS
  events/connections/storage, fail over or restore, then verify migration and
  tenant-scoped counts before reopening.
- **S3/object storage:** readiness fails; preserve database metadata, inspect
  IAM/endpoint/bucket policy, recover object versions, and verify checksums.
- **Valkey:** readiness and protected requests fail closed. Restore cache access;
  queue jobs are non-authoritative and may need idempotent reconciliation from
  PostgreSQL state. Phase 7 does not claim a Redis DLQ.
- **OIDC:** existing unexpired application sessions continue; new sign-in fails.
  Validate discovery/JWKS/client configuration and restart login after recovery.
- **Bedrock:** governed generation reports safe failure; existing evidence and
  deterministic workflow state remain accessible. No fabricated fallback.
- **Telemetry:** application operation continues within exporter bounds; restore
  the private collector and confirm correlation continuity.

## Backup and restore

RDS automated backups retain 14 days in the reference foundation; Multi-AZ is
availability, not backup. S3 versioning retains noncurrent document versions
for 90 days. Local recovery verification uses `phase7-backup-restore-test.sh`,
which dumps the active Compose database, restores into an isolated database,
and verifies claim/document counts and migration revision before deleting the
test database. Production must perform an RDS restore into an isolated network,
validate application reads and object integrity, then record achieved RPO/RTO.
The target remains RPO 15 minutes and RTO 4 hours; it is an objective, not a
verified cloud result.

## Load and resilience commands

```bash
./scripts/phase7-load-test.sh smoke
./scripts/phase7-resilience-test.sh
./scripts/phase7-backup-restore-test.sh
```

Normal and stress load profiles are intentionally opt-in. Resilience testing
stops and restores local Redis, MinIO, and PostgreSQL, then restarts API/worker;
run it only against the synthetic local Compose stack.

