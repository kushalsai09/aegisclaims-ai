# Authorization Model

## Model

Authorization combines RBAC with tenant/resource attributes and contextual constraints:

`permit = active_subject AND tenant_match AND role_allows_action AND resource_scope_allows AND context_allows AND NOT explicit_deny`

The policy is evaluated server-side before resource data is loaded or a presigned object URL is created. The same policy functions apply to REST, queue workers, workflow nodes, retrieval, reviews, exports, and operations views.

## Roles and representative actions

| Action | Adjuster | Supervisor / Reviewer | Compliance / Operations |
|---|---:|---:|---:|
| Read assigned claim and authorized documents | Yes | Review-scope claims | Only separately granted samples |
| Start/retry allowed analysis | Yes | Yes within review scope | No by default |
| Submit artifact feedback/edit proposal | Yes | Yes | Findings only |
| Approve/reject/return review task | No | Yes, assigned/eligible | No by default |
| View claim audit timeline | Assigned claim | Review-scope claim | Authorized sample/projection |
| Run golden evaluation | No | No by default | Yes |
| View aggregate quality/cost dashboard | Limited personal/work view | Queue view | Yes |
| Change rules/prompts/model policy | No | No | Separate administrator role, not one of the three personas |

Absence of a permission is a deny. A future configuration administrator is intentionally separate from operational reviewer authority.

## Resource attributes

Tenant, claim assignment/team, review assignment/queue, document access label, policy corpus scope, artifact snapshot, data classification, workflow status, environment, and legal-hold/export restrictions. Claim access does not automatically grant unrestricted evaluation export or raw model trace access.

## Identity propagation

The API validates OIDC and maps `issuer + subject` to a local active user. It creates a signed/internal request context containing actor ID, tenant, session/authentication metadata, correlation, and evaluated scopes. Workers receive workload identity and a constrained delegated context reference, not a reusable employee bearer token.

## Document and retrieval enforcement

Document metadata is authorized before object access. Retrieval queries require a non-optional authorization scope; backend predicates include tenant and allowed resource/access labels. Returned chunks are revalidated before prompt assembly. Citation opening performs a fresh authorization check.

## Human-review enforcement

A decision requires an eligible reviewer, active task, matching tenant/queue, allowed transition, expected task/artifact/input-snapshot versions, and mandatory reason. The actor who prepared an artifact may be prevented from approving it when a **SYNTHETIC DEMONSTRATION RULE** requests separation of duties.

## Administration and break glass

Configuration changes require a distinct privileged role, peer review, immutable version, and audit. A future break-glass path must be time-bound, strongly authenticated, reasoned, alerted, and retrospectively reviewed; it is not implemented as a hidden superuser bypass.

## Tests

Maintain a policy decision table and property-based tests for every role/action/resource combination, cross-tenant IDs, unassigned claims, stale assignments, disabled users, forged claims, queue consumers, document URLs, retrieval filters, and review replay. Authorization coverage is a blocking release gate.
