# API Architecture

## Style and contract

FastAPI exposes resource-oriented REST APIs described by OpenAPI. Pydantic schemas are distinct from persistence and domain objects. The initial namespace is `/api/v1`; breaking changes require a new version or additive migration plan. JSON uses UUID strings, RFC 3339 UTC timestamps, explicit enums, and structured problem responses.

## Boundaries

| Area | Representative endpoints | Notes |
|---|---|---|
| Session | `GET /me`, `GET /me/permissions` | Derived server-side; no sensitive tokens returned |
| Claims | `GET /claims`, `GET /claims/{id}`, `GET /claims/{id}/workspace` | Filtered by tenant/assignment/role |
| Documents | `POST /claims/{id}/document-uploads`, `POST /document-uploads/{id}/complete`, `GET /documents/{id}` | Two-step scoped upload; object authorization remains server-owned |
| Workflows | `POST /claims/{id}/analyses`, `GET /analyses/{id}`, `POST /analyses/{id}/cancel` | Asynchronous commands with idempotency |
| Evidence | `GET /analyses/{id}/evidence`, `GET /citations/{id}/source` | Source span authorization on every access |
| Reviews | `GET /review-tasks`, `GET /review-tasks/{id}`, `POST /review-tasks/{id}/decisions` | Optimistic concurrency and reason required |
| Feedback | `POST /artifacts/{id}/feedback` | Append-only and rate controlled |
| Audit | `GET /claims/{id}/timeline`, `GET /audit/events` | Role- and purpose-restricted projections |
| Evaluation | `POST /evaluation-runs`, `GET /evaluation-runs/{id}` | Authorized operations role; immutable config manifest |
| Operations | `GET /health/live`, `GET /health/ready` | Readiness avoids leaking dependency secrets |

## Command semantics

Mutating requests accept an `Idempotency-Key`; the server binds it to actor, tenant, route, and request hash. Reuse with a different payload returns conflict. Aggregate updates require an `If-Match` or explicit expected version. Accepted asynchronous work returns `202`, a status resource, and retry guidance—not a false completed response.

## Errors

Errors follow a problem-details shape with stable `code`, safe `detail`, correlation ID, retryability, and field violations. Authentication is `401`; authenticated but forbidden resource access is `403` or a policy-selected non-enumerating `404`; stale versions are `409`; validation is `422`; rate limits are `429`; unavailable dependencies are `503`. Stack traces, provider bodies, prompts, and document text never enter client errors.

## Authentication and authorization

The API validates OIDC issuer, audience, signature, expiry, nonce/state where applicable, and token type. It maps the subject to an active tenant user and evaluates action/resource policy before loading sensitive content. Workload consumers use separate machine identity. The frontend never supplies an authoritative role or tenant ID.

## Progress delivery

`GET /analyses/{id}/events` uses server-sent events with monotonically increasing event IDs, heartbeat, authorization recheck, and reconnect cursor. Events contain safe statuses and references, not unrestricted model output. Polling `GET /analyses/{id}` remains the compatibility fallback.

## Internal events

Versioned event envelopes contain event ID, type/version, occurred time, tenant, aggregate ID/version, correlation/causation IDs, producer, data classification, and typed payload. Consumers deduplicate event IDs. The transactional outbox prevents committing domain state without its event.

## Contract governance

OpenAPI and event schemas are linted, diffed for breaking changes, and exercised by consumer/provider contract tests. Generated clients are optional; shared source-code models must not couple Vue to Python internals. Examples use synthetic identifiers only.
