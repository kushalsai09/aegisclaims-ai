# ADR-012: Redis Queue and Rate-Limit Boundary

**Status:** Accepted for Phase 7

## Decision

Use TLS ElastiCache Valkey for the implemented production queue adapter and
shared fixed-window rate limiting. PostgreSQL remains authoritative; Redis data
must be reconstructible or safely reconciled. Reject protected work when the
rate-limit store is unavailable.

## Rationale and consequences

This preserves the Phase 2–6 Redis adapter and keeps the first deployment
operationally small. It does not provide SQS durability, DLQ/redrive, or a
transactional outbox. Those are preferred future additions if measured job
loss/replay requirements justify them. Worker jobs must remain idempotent and
operators must reconcile incomplete PostgreSQL state after cache recovery.

