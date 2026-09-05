# Data Architecture

## Principles

PostgreSQL is authoritative for transactional state and metadata. Object storage is authoritative for immutable document bytes and large derived artifacts. Search tables/indexes are rebuildable. Audit events are append-only. Every tenant-owned table includes `tenant_id`, even though the first release contains one fictional organization.

## Core relational schema

| Table | Key fields and relationships | Notes |
|---|---|---|
| `tenants` | `id`, `name`, status | One fictional seed tenant; no implicit global tenant |
| `users` / `roles` / `user_roles` | OIDC subject, tenant, role | Claims from IdP are mapped, not trusted as resource authorization alone |
| `claims` | tenant, claim number, policy, loss timestamp, status, version | Optimistic concurrency and soft lifecycle state |
| `claim_assignments` | claim, user/team, assignment type, interval | Resource-level access input |
| `policies` | tenant, synthetic policy number, product | Fictional only |
| `policy_editions` | policy/product edition, effective interval, supersedes | Governing-version resolution |
| `endorsements` | policy edition, effective interval, precedence metadata | Explicit applicability |
| `documents` | tenant, claim/policy owner, type, access label | Logical document |
| `document_versions` | object URI, checksum, MIME, size, status | Immutable accepted version |
| `document_extractions` | version, extractor/schema version, object/text refs | Reproducible derived output |
| `document_chunks` | version, text/provenance, FTS vector, embedding ref/vector | Derived, index-versioned |
| `facts` | claim, fact type/value, source span, method, verification | Conflicting values coexist |
| `workflow_runs` | claim, graph/version, snapshot, status, correlation | Durable run identity |
| `workflow_checkpoints` | run, state schema/version, checkpoint | Encrypted/purged per policy |
| `retrieval_runs` / `retrieval_results` | query/filter/config and ranked chunks | Evaluation/audit lineage |
| `rule_definitions` / `rule_results` | rule/version/label, run, result, evidence | Rules requiring business assumptions carry the demonstration label |
| `generated_artifacts` | run, type, schema/prompt/model versions, body ref | Immutable versions; citations separate |
| `citations` | artifact assertion, chunk/source span, validation state | Referential and applicability validation |
| `support_assessments` | run, component signals, risk, escalation reasons | No naive confidence field |
| `review_tasks` / `review_decisions` | run/artifact snapshot, assignee, status, decision/reason | Unique active task by trigger/snapshot |
| `feedback` | artifact, actor, structured ratings/corrections | Append-only from artifact perspective |
| `audit_events` | tenant, actor/workload, action, resource, correlation, hash chain | Append-only partitioned store |
| `outbox_events` | aggregate/version, event type/payload, publish state | Transactional event publication |
| `evaluation_datasets` / `cases` / `runs` / `results` | immutable manifests and metrics | Candidate/baseline reproducibility |
| `model_invocations` | task/provider/model/prompt, usage, cost, latency, outcome | Content minimized/referenced |

## Version and temporal rules

- IDs are UUIDs; business identifiers are unique within tenant.
- Mutable aggregates carry integer versions for optimistic concurrency.
- Policy and endorsement applicability uses half-open effective intervals and explicit loss timestamps.
- Document bytes are immutable. Corrections create a new version and stale dependent analyses.
- Timestamps are stored in UTC; original source timezone/precision is retained when meaningful.
- Prompts, schemas, graphs, rules, retrieval configs, model policies, and datasets use immutable semantic or content-addressed versions.

## Object layout

Object keys are non-guessable and partitioned by environment/tenant/resource/version, never by raw customer names. Classes include quarantined uploads, accepted originals, normalized text/layout, page renderings, evaluation artifacts, and controlled exports. Database metadata owns authorization; object paths do not confer it.

## Tenant and row isolation

Application queries require tenant context and include tenant predicates. Foreign keys include or validate tenant ownership. PostgreSQL row-level security may provide defense in depth but does not replace application authorization. Connection pools do not retain actor context between requests. Cross-tenant evaluation aggregates use de-identified authorized projections.

## Synthetic data model

The HarborView HomeSecure dataset uses deterministic generators, fictional address ranges, reserved/example contact domains, manifests, scenario labels, source templates, and expected outcomes. A scanner blocks known real identifiers and unapproved source text. Each case records seed, generator version, policy edition, loss date, expected evidence, expected issues, and expected escalation.

## Retention and deletion

Exact periods require organizational policy and are configuration, not invented regulation. The architecture supports per-class retention, legal-hold flags, deletion approvals, object/version/index propagation, tombstone audit events, and reconciliation. Audit integrity does not mean retaining unrestricted content forever: events can retain hashes and identifiers after allowed content deletion.

## Backup and recovery

Database point-in-time recovery and encrypted snapshots, S3 versioning, Terraform state protection, and exportable configuration manifests are tested through scheduled restores. Derived indexes are rebuilt from authoritative data and version manifests.
