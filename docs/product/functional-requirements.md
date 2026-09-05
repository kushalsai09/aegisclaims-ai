# Functional Requirements

IDs are stable traceability keys. “Shall” denotes a release acceptance requirement.

## Identity and access

- **FR-001:** The system shall authenticate employees through a provider-neutral OIDC boundary.
- **FR-002:** It shall enforce tenant, role, assignment, resource, and action authorization server-side on every claim, document, review, export, and tool operation.
- **FR-003:** It shall expose Claims Adjuster, Supervisor/Human Reviewer, and Compliance/Operations Reviewer roles with least-privilege permissions.

## Claims and documents

- **FR-010:** It shall create, list, and view synthetic claims and their versioned structured records.
- **FR-011:** It shall accept allowlisted file types and sizes, calculate checksums, quarantine uploads, and preserve immutable originals.
- **FR-012:** It shall track scanning, extraction, classification, chunking, embedding, and indexing status independently and support safe retry.
- **FR-013:** It shall retain page/section/character provenance from normalized text to the source object.
- **FR-014:** It shall mark extracted facts with source, extraction method, schema version, and verification status.

## Knowledge and retrieval

- **FR-020:** It shall store fictional policy editions, endorsements, effective periods, and lineage.
- **FR-021:** It shall perform hybrid semantic and keyword retrieval with tenant, claim, document type, policy identity, edition, and effective-date filters.
- **FR-022:** It shall return ranked evidence objects, not unstructured text blobs.
- **FR-023:** It shall validate that citations refer to an authorized, retrievable source span and the input snapshot used by the workflow.
- **FR-024:** It shall record query, filters, retrieval configuration, candidates, ranks, and selected evidence for evaluation and audit subject to retention policy.

## Decision support

- **FR-030:** It shall produce schema-validated summaries, facts, missing-information items, contradictions, policy evidence, unresolved issues, and proposed next actions.
- **FR-031:** It shall apply versioned deterministic rules and label every domain threshold **SYNTHETIC DEMONSTRATION RULE**.
- **FR-032:** It shall calculate a Support Assessment from measurable component signals without asking the LLM for a self-confidence percentage.
- **FR-033:** It shall refuse or abstain when evidence is insufficient, unauthorized, stale, or unsupported.
- **FR-034:** It shall never expose private chain-of-thought; concise rationale shall consist of evidence, rules, issue codes, and workflow outcomes.
- **FR-035:** It shall prohibit automated coverage approval/denial, payment, fraud accusation, legal conclusion, and unapproved external communication.

## Workflow and human review

- **FR-040:** It shall persist versioned LangGraph state and support idempotent start, retry, cancel, and resume operations.
- **FR-041:** It shall create mandatory review tasks for configured missing critical evidence, contradictions, unsupported answers, policy ambiguity, failed rules, high-risk categories, and consequential proposed actions.
- **FR-042:** Reviewers shall approve, reject, edit, or return an artifact with a reason, subject to authorization and optimistic concurrency.
- **FR-043:** The system shall prevent resume when the review task, actor, input snapshot, or artifact version is stale.
- **FR-044:** It shall notify the UI of asynchronous progress using resumable server-sent events or polling fallback.

## Audit, feedback, and evaluation

- **FR-050:** It shall append tamper-evident audit events for access, workflow transitions, retrieval, model calls, tool calls, rule results, reviews, feedback, and configuration changes.
- **FR-051:** It shall record model/provider/version, prompt version, graph version, retrieval version, latency, token usage, estimated cost, errors, and final status.
- **FR-052:** Employees shall submit structured usefulness and error feedback without overwriting generated artifacts.
- **FR-053:** Authorized users shall run frozen golden datasets and compare candidate and baseline results.
- **FR-054:** Deployment gates shall consume deterministic, retrieval, generation, agent, latency, and cost metrics.

## Synthetic dataset

- **FR-060:** The seed dataset shall include all ten approved scenario classes and expected evidence, abstention, issue, and escalation annotations.
- **FR-061:** Generation shall be seeded and reproducible, contain no real PII, and include machine-readable manifests and provenance.
