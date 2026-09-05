# Phase 4 Controlled Workflows

## Implemented boundary

Phase 4 coordinates a bounded claim evidence review. A typed LangGraph `StateGraph` routes five narrow nodes: load context, retrieve existing Phase 3 evidence, validate provenance, determine review requirements, and prepare a structured artifact. The graph has no model tools, shell, filesystem, SQL, HTTP, browser, credential, or external-action capability.

The deterministic Phase 3 retrieval and local extractive generator remain the evidence foundation. No paid model is used and the UI identifies outputs as system-generated proposals rather than claim decisions.

## Lifecycle

`created → gathering_evidence → evaluating_evidence → determining_review_requirements → completed | awaiting_human_review`

Explicit alternate states are `insufficient_evidence`, `conflicting_evidence`, `ambiguous_evidence`, `failed`, `awaiting_additional_information`, and `cancelled`. Evidence states are checkpointed while processing; the final routing state determines whether the workflow stops or creates a unique human-review task.

Human review is mandatory for missing/insufficient support, material conflicts, material ambiguity, untrusted instruction content, and scenarios carrying a mandatory-review rule. Review actions are authenticated and server-authorized, recheck claim access, require the current checkpoint version, preserve the actor/reason/correlation ID, and use an idempotency key. Stale submissions return HTTP 409.

## Durable checkpoints and resume

PostgreSQL application tables—not an opaque framework store—are authoritative:

- `workflow_runs` stores current state, input fingerprint, retry budget, and optimistic checkpoint version.
- `workflow_checkpoints` stores versioned reference-oriented typed state after every material node.
- `workflow_events` is append-only transition history.
- `review_artifacts` stores structured evidence references, signals, citations, and proposals.
- `workflow_review_actions` stores idempotent actor-attributed review/retry actions.
- `human_review_tasks` remains the shared review queue.

Native LangGraph interrupt persistence is intentionally not used. It would duplicate lifecycle state outside the application authorization model. Waiting is represented as a durable `awaiting_human_review` checkpoint; an authorized API resume applies a version-checked transition. API and worker processes can therefore restart without losing state or holding an in-memory execution.

## Freshness and provenance

The workflow fingerprints the task and sorted source-document checksums. Checkpoints contain evidence references and checksums, not duplicated document bodies. Citations preserve tenant-scoped claim/document/page/chunk IDs, source offsets, page/source checksums, policy applicability, rank, and retrieval configuration. A citation whose claim ID does not match the workflow fails provenance validation.

## Consequential-action boundary

Artifacts may only propose evidence work, such as requesting a missing document or inspecting conflicting sources. The system never approves or denies a claim, determines authoritative coverage/liability/fraud, calculates or issues payment, contacts an external party, changes policies or source documents, or closes a claim. Human acknowledgement approves only the review artifact/proposal—not a claim outcome.

## Failure and retry

Validation, authorization, stale-state, and lifecycle conflicts are explicit API errors. Node failures become `failed` with a bounded detail and a durable checkpoint. Authorized retries are limited to two and are allowed only from `failed` or `awaiting_additional_information`. There is no unbounded retry loop.

