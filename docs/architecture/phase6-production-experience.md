# Phase 6 Production Experience

The product experience is organized around employee work rather than implementation phases. The shell exposes My Work, Claims, Reviews, Operations, and Evaluation according to role. Account identity, organization, role, and sign-out live in a restrained account menu. One persistent local/synthetic indicator replaces repeated demonstration banners.

The design system centralizes typography, spacing, borders, radii, surfaces, semantic states, focus treatment, and content widths in CSS variables. Surfaces are primarily structural; status chips are reserved for state. Tables convert to intentionally grouped records on narrow screens instead of retaining unusable desktop columns.

My Work prioritizes assigned claims, review workload, recently updated cases, and conditions requiring attention. Claims provides real client-side search, deterministic workflow filtering, and sorting over the authorized result set. The claim workspace uses a claim header and section navigation for overview, documents and evidence, the subordinate AI-assisted Evidence Brief, and workflow/human review. Provider identifiers and correlation details are placed under technical disclosure rather than shown to adjusters by default.

Document detail separates source-document metadata, extracted text, structured facts, source spans, conflicts, processing history, and technical provenance. Reviews present claim, reason, safety flags, workflow state, age, and assignment. Reviewer rationale explicitly explains its audit and decision consequences. Operations and Evaluation are separate and role-restricted.

The synchronous brief-generation decision is retained. Retrieval and deterministic generation are currently bounded and complete within the request lifecycle; introducing a second asynchronous artifact protocol would add recovery and polling complexity without a measured need. A future real-provider load test may justify moving generation to the existing Redis worker, with persisted job state and idempotency preserved.
