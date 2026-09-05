# Incident and Failure Strategy

## Failure taxonomy

- **Validation:** malformed request/file/output, unsupported schema.
- **Authorization/security:** denied access, injection signal, blocked tool, malware suspicion.
- **Evidence/quality:** insufficient retrieval, invalid citation, policy ambiguity, contradiction.
- **Dependency:** database, object store, queue, identity, model, embedding, telemetry unavailable.
- **Capacity/cost:** throttling, quota, queue backlog, token/cost budget exceeded.
- **Consistency:** stale snapshot, duplicate delivery, partial index, audit/outbox mismatch.
- **Software/deployment:** regression, migration incompatibility, bad configuration.

Each class has safe user status, retryability, owner, alert threshold, runbook, and audit/telemetry requirements.

## Graceful behavior

- Read views distinguish authoritative, pending, stale, partial, abstained, interrupted, and failed states.
- Model failure may leave deterministic facts/rules available but cannot yield a fabricated completed summary.
- Retrieval or citation failure produces unsupported/ambiguous status and review when required.
- Queue retries use exponential backoff with jitter; poison messages enter DLQ with safe replay tooling.
- Circuit breakers stop cascading failures and denial-of-wallet retries.
- Audit persistence failure blocks review decisions and configured consequential transitions.
- Telemetry exporter failure buffers within bounds and alerts; buffer exhaustion must not exhaust the application.

## Idempotency and reconciliation

API commands, jobs, graph nodes with effects, review creation, and event consumers have durable idempotency keys and uniqueness constraints. A transactional outbox connects state and event publication. Scheduled reconciliation checks accepted objects vs metadata, ingestion/index states, outbox lag, queue/DLQ, active review uniqueness, expired/stale tasks, and audit sequence gaps.

## Incident lifecycle

1. Detect through alerts, employee report, evaluation gate, or security signal.
2. Triage severity, affected versions/tenants/resources, data exposure, and ongoing harm.
3. Contain using configuration rollback, provider/task disable, queue pause, document quarantine, credential revocation, or access restriction.
4. Preserve authorized evidence: release manifests, safe traces, audit events, hashes, and affected IDs.
5. Recover from known artifact/config, redrive idempotently, rebuild derived index, or restore authoritative data.
6. Communicate status and limitations without exposing sensitive content.
7. Complete blameless review, control/test improvement, synthetic regression case, and tracked actions.

## Priority examples

- **Critical:** cross-tenant disclosure, unauthorized consequential action, compromised credentials, accepted malicious execution.
- **High:** wrong policy version presented as governing at scale, fabricated citations passing validation, audit integrity failure, missed mandatory review.
- **Medium:** model outage with safe degradation, sustained backlog, cost anomaly, partial telemetry.
- **Low:** isolated UI defect or noncritical evaluator delay.

Final severities and response times require organizational ownership and are not represented as real insurer policy.

## Runbooks required before production-like use

Model/provider outage, identity outage, database failover/restore, S3 access/scan failure, SQS backlog/DLQ redrive, bad prompt/model/retrieval release, index corruption/rebuild, leaked credential, cross-scope access alert, prompt-injection campaign, audit gap, and runaway cost.

## Recovery validation

Quarterly is a proposed demonstration cadence—not a regulatory claim—for restore, DLQ, rollback, key/secret rotation, and tabletop exercises. Results record achieved RPO/RTO, gaps, owners, and deadlines.
