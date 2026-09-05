# Security Architecture

## Objectives

Protect claim and policy data, preserve employee accountability, prevent untrusted content from controlling the system, constrain models and tools, and produce reliable audit evidence. The demonstration uses synthetic data, but its control boundaries assume production-sensitive documents.

## Trust boundaries

1. Browser to public edge.
2. Edge to API container.
3. API/worker to data stores and queues.
4. Application to model/embedding providers.
5. Quarantine to accepted document storage.
6. Retrieval corpus to prompt construction.
7. Model output/tool proposal to authorized application operation.
8. Operational telemetry/evaluation stores to reviewers.

Every crossing validates identity, authorization, schema, classification, size/budget, and provenance appropriate to the boundary.

## Control layers

### Identity and access

- Standards-based OIDC for employees; short-lived workload credentials for services.
- Deny-by-default RBAC plus tenant, assignment, resource, action, and context checks.
- Separate API, worker, deployment, evaluation, and read-only operations roles.
- Step-up or reauthentication integration point for consequential human actions.
- Periodic access review and immediate subject/assignment revocation behavior.

### Data protection

- TLS in transit and KMS-backed encryption at rest in AWS.
- Immutable/versioned originals, scoped object access, checksums, and reconciliation.
- Secrets Manager for runtime secrets; CI uses OIDC rather than stored AWS keys.
- Content minimization in prompts, logs, traces, evaluation artifacts, and exports.
- Configurable retention, holds, deletion propagation, and key separation by environment.

### Application and supply chain

- Pydantic and frontend schema validation, output encoding, CSRF/CSP protections, rate and size limits.
- Allowlisted document types verified by magic bytes; archive expansion and parser resource limits; malware-scan interface; sandboxed parsing where feasible.
- Locked dependencies, SBOMs, source/image/IaC scanning, signed artifacts, protected branches, and provenance attestations.
- Non-root, read-only containers with dropped Linux capabilities, minimal images, and restricted egress.

### AI-specific controls

- Treat all retrieved text as untrusted quoted data.
- Separate system policy, employee request, and evidence channels with explicit delimiters and identifiers.
- Models receive only authorized, task-minimal evidence.
- Strict output schemas, citation validation, prohibited-action checks, and bounded token/tool budgets.
- Tool registry allowlists calls by graph node and identity; no shell, arbitrary HTTP, raw SQL, or filesystem tool.
- Prompt-injection detection is defense in depth, not the authorization boundary.
- High-risk/unsupported outcomes interrupt for human review.

## Audit integrity

Security-relevant actions create append-only events with actor/workload identity, tenant, action, resource, outcome, reason, correlation, configuration versions, and predecessor/event hashes. High-value state transitions use a transactional outbox so audit intent commits with domain state. S3 Object Lock or an external immutable archive is an optional production control after retention requirements are approved.

## Key security success criteria

- No cross-tenant or cross-assignment access in authorization tests.
- No model or document instruction can invoke an unauthorized tool.
- No accepted file bypasses validation/quarantine status.
- No consequential workflow completes without an authorized, current human decision.
- Secrets and unrestricted evidence do not appear in logs, traces, images, or frontend bundles.
- Threat-model abuse cases and incident runbooks are exercised before release.

## Shared responsibility

Managed AWS services reduce infrastructure operations but do not authorize application resources, validate citations, classify data, select safe prompts, constrain tools, or determine retention. Those remain application and organizational responsibilities.
