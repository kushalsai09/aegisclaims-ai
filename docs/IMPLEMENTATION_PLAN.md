# Dependency-Ordered Implementation Plan

## Guardrails for all milestones

No milestone may weaken the decision-support boundary, bypass server-side authorization, introduce real PII/proprietary carrier material, or require paid credentials for CI. Domain thresholds are labelled **SYNTHETIC DEMONSTRATION RULE**. Each milestone updates documentation, threat model, evaluation cases, telemetry, and ADRs when its behavior changes.

The expected future repository is organized as `apps/api`, `apps/worker`, `apps/web`, platform and domain packages under `packages`, `data/synthetic` and `data/golden`, versioned `prompts`, database `migrations`, `infrastructure/docker` and `infrastructure/terraform`, cross-cutting `tests`, scripts, and GitHub workflows. File names below are expectations, not implementation created in this documentation phase.

## Milestone 0 — Repository and engineering foundation

**Objective:** Establish reproducible tooling and quality gates without application behavior.

**Components:** Git metadata, Python and Node workspaces, task runner, configuration conventions, pre-commit, CI skeleton, documentation validation, licenses, ownership.

**Expected files/modules:** `pyproject.toml`, `uv.lock` or selected Python lockfile, `package.json`, frontend lockfile, `.editorconfig`, `.env.example`, `.gitignore`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `scripts/validate_docs.*`, root `README.md`, `CONTRIBUTING.md`.

**Acceptance criteria:** Pinned supported runtimes; one local check command; CI runs without secrets; Mermaid and Markdown links validate; no application endpoint exists.

**Tests required:** Toolchain smoke, secret scan, dependency lock consistency, docs link/Mermaid parse.

**Dependencies:** Approved documentation baseline.

**Risks:** Overbuilding tooling; platform-specific scripts; dependency drift.

**Definition of done:** Clean checkout can install from lockfiles and run identical green validation locally and in CI with documented commands.

## Milestone 1 — Walking skeleton and local infrastructure

**Objective:** Prove API, worker, web, storage, queue, telemetry, and database wiring with no AI behavior.

**Components:** FastAPI health endpoints, Vue shell, PostgreSQL/pgvector, MinIO, local/mock queue, OpenTelemetry Collector, typed settings, Compose profiles.

**Expected files/modules:** `apps/api`, `apps/worker`, `apps/web`, `packages/contracts`, `packages/observability`, `packages/config`, `infrastructure/docker/compose.yaml`, initial `migrations`.

**Acceptance criteria:** API liveness/readiness; web displays safe environment/status; worker consumes an idempotent test job; trace crosses API/outbox/worker; startup rejects mock auth/model adapters outside local/test.

**Tests required:** Unit settings, container health, migration, adapter contract, telemetry smoke, Compose end-to-end.

**Dependencies:** M0.

**Risks:** False production parity; flaky container startup; leaking local shortcuts.

**Definition of done:** One documented command starts/stops the stack; smoke suite is repeatable offline; CI captures logs on failure.

## Milestone 2 — Identity, tenant context, and authorization

**Objective:** Make every subsequent capability secure by default.

**Components:** OIDC verification port, local development identity, users/roles/assignments, authorization policy service, request/workload contexts, audit foundation.

**Expected files/modules:** `packages/security/identity`, `packages/security/authorization`, `packages/domain/identity`, API auth dependencies/middleware, authorization migrations and fixtures.

**Acceptance criteria:** Three approved personas; tenant/resource/action checks before lookup; disabled/stale identities denied; workload identity distinct; decisions audit safe context.

**Tests required:** Policy decision table, property-based cross-tenant/role/assignment tests, forged token/claims, object-ID enumeration, worker delegation, frontend route UX tests.

**Dependencies:** M1.

**Risks:** Treating token roles as sufficient; connection context leakage; test stub enabled in production.

**Definition of done:** All protected example routes deny by default and pass horizontal/vertical privilege tests; threat model evidence is linked.

## Milestone 3 — Synthetic product, claims, and policy domain

**Objective:** Create an internally consistent fictional domain and reproducible scenario manifests.

**Components:** HarborView HomeSecure HO-SYN-01 product model, policy editions/endorsements/effective periods, claim aggregate, ten scenario families, generator and validators.

**Expected files/modules:** `packages/domain/claims`, `packages/domain/policies`, `packages/rules`, `data/schemas`, `data/synthetic/templates`, `data/synthetic/manifests`, `scripts/generate_synthetic_data.*`.

**Acceptance criteria:** Seeded output hashes are reproducible; loss date resolves expected edition except intentional ambiguity; no real PII/proprietary text; every threshold bears the demonstration label.

**Tests required:** Schema, temporal/property, cross-reference, determinism, PII-pattern scan, license/provenance, scenario completeness.

**Dependencies:** M0; integrates with M2 persistence.

**Risks:** Unrealistic yet overclaimed rules; template leakage; inconsistent dates/provenance.

**Definition of done:** A frozen dataset version produces all approved scenarios and expected machine-readable outcomes with human-reviewed safety cases.

## Milestone 4 — Secure document ingestion

**Objective:** Accept and process synthetic documents while preserving integrity and provenance.

**Components:** Upload intent, quarantine, validation, scan port, immutable object versions, extraction/layout adapter, classification, normalized text, chunks, status/retry.

**Expected files/modules:** `packages/domain/documents`, `packages/documents/ingestion`, `packages/storage`, worker handlers, document APIs, migrations, synthetic document renderers.

**Acceptance criteria:** Type/size/magic/checksum limits; no active content rendering; exact source offsets/page metadata; partial/failure states; duplicate delivery safe; authorized object access only.

**Tests required:** Malformed/polyglot/archive-limit fixtures, checksum, idempotency, parser timeouts, OCR/noise, prompt-injection preservation/flagging, cross-tenant access, provenance round trip.

**Dependencies:** M1–M3.

**Risks:** Parser vulnerabilities, offset drift, malware scanner unavailable, oversized artifacts.

**Definition of done:** Every synthetic document reaches a correct ready/partial/rejected state and its normalized span opens the matching original location.

## Milestone 5 — Hybrid retrieval baseline

**Objective:** Retrieve authorized, governing evidence with measurable quality before generation.

**Components:** FTS and pgvector backend, deterministic embedding mock, Bedrock-compatible embedding port, hard filters, rank fusion, index manifests, evidence/citation contracts, benchmark runner.

**Expected files/modules:** `packages/retrieval/contracts`, `packages/retrieval/postgres`, `packages/ai_gateway/embeddings`, index migrations, `data/golden/retrieval`, evaluation runner.

**Acceptance criteria:** Tenant/access/policy/effective-date filters are mandatory; wrong-edition hard negatives rejected; evidence retains provenance/stage scores; index version can build and atomically activate.

**Tests required:** Backend contracts, SQL/property authorization, recall@k/nDCG/MRR/version accuracy, concurrency/latency baseline, deletion/index reconciliation, noisy/distractor/unanswerable queries.

**Dependencies:** M3–M4.

**Risks:** Tiny benchmark optimism, raw-score fusion error, database load, chunking overfit.

**Definition of done:** Approved retrieval baseline and immutable manifest meet declared slice thresholds with zero scope violations.

## Milestone 6 — Model gateway and structured AI tasks

**Objective:** Add language capabilities without provider coupling or uncontrolled output.

**Components:** `ModelGateway`, deterministic mock, task/model policies, prompt registry, structured extraction/synthesis/contradiction tasks, budgets, usage and price catalog, Bedrock adapter behind a feature flag.

**Expected files/modules:** `packages/ai_gateway/models`, `packages/ai_gateway/providers/mock`, later `providers/bedrock`, `prompts/*`, Pydantic output schemas, model-invocation persistence.

**Acceptance criteria:** CI offline; strict schemas; bounded syntax repair; citations use supplied IDs only; task budgets enforced; provider metadata/usage reconstructable; prohibited decisions blocked.

**Tests required:** Provider contract, snapshot/golden outputs, schema fuzzing, timeout/throttle/error normalization, injection and citation-forgery tests, token/cost budgets, optional Bedrock integration suite.

**Dependencies:** M3, M5; security from M2.

**Risks:** Abstraction loses provider features; nondeterminism; cost; prompt leakage; judge correlation.

**Definition of done:** Mock passes all contracts and golden tasks; an approved Bedrock candidate can be evaluated without domain/workflow code changes.

## Milestone 7 — Deterministic rules and Support Assessment

**Objective:** Turn evidence quality and domain checks into explainable, testable support signals.

**Components:** Required-field/policy applicability/citation/risk rules, contradiction normalization, Support Assessment builder, escalation policy and reason codes.

**Expected files/modules:** `packages/rules/engine`, `packages/rules/synthetic_residential`, `packages/domain/support`, `packages/evaluation/support`, rule/config schemas and migrations.

**Acceptance criteria:** No naive confidence field; components trace to inputs/results; critical failures cannot be averaged away; demonstration labels visible; LLM cannot override signals.

**Tests required:** Exact rule tables, mutation and branch coverage, temporal boundaries, component invariants, mandatory scenario escalation recall, false-escalation analysis.

**Dependencies:** M3, M5, M6 citation schemas.

**Risks:** Arbitrary composite scoring, hidden policy assumptions, duplicated graph logic.

**Definition of done:** Each golden case produces expected signals, reasons, and risk/escalation state deterministically.

## Milestone 8 — LangGraph claims workflow

**Objective:** Compose the reference decision-support workflow with durable, bounded behavior.

**Components:** Typed state, approved nodes/edges, checkpoint adapter, tool registry, retry/error policy, immutable input snapshots, audit/trace instrumentation, artifact validation/finalization.

**Expected files/modules:** `packages/workflows/claims/state.py`, `graph.py`, `nodes`, `routing`, `tools`, checkpoint migrations, worker orchestration handlers.

**Acceptance criteria:** Explicit paths; no model-selected routing; bounded read tools; restart/replay safe; partial/abstain/fail distinct; outputs pinned to full version manifest.

**Tests required:** Node units, transition tables, expected-path golden tests, tool choice/argument/authorization, crash/restart, duplicate job, retry exhaustion, cost/latency capture, prohibited-action scenarios.

**Dependencies:** M2, M4–M7.

**Risks:** State bloat, framework leakage, double orchestration, side-effect replay.

**Definition of done:** All ten scenario families terminate in their expected completed/abstained/review/failed state with reconstructable trace and audit.

## Milestone 9 — Human review and employee APIs

**Objective:** Enforce human control through durable review tasks and stable contracts.

**Components:** Review queue/assignment, interrupt persistence, decisions, optimistic concurrency, resume authorization, claims workspace APIs, SSE progress, feedback and audit timeline.

**Expected files/modules:** `packages/domain/reviews`, application review services, API routers/contracts, outbox events, graph resume integration, review migrations.

**Acceptance criteria:** Mandatory triggers create one task per snapshot; reviewers can approve/edit/reject/return with reason; stale/unauthorized/replayed decisions fail; no process waits while interrupted.

**Tests required:** Role/queue matrix, concurrency, idempotency, stale evidence, separation-of-duties demonstration rule, SSE reconnect, outbox/audit failure, end-to-end interrupt/resume.

**Dependencies:** M8 and M2.

**Risks:** Rubber-stamping UX, duplicate tasks, stale approval, ambiguous meaning of “approve.”

**Definition of done:** Human-reviewed golden cases demonstrate correct queue, evidence snapshot, decision, resume, final state, and complete audit.

## Milestone 10 — Polished Vue employee experience

**Objective:** Deliver the accessible internal claims and review workspace.

**Components:** Design tokens/components, My Work, Claims, Claim Workspace panels, evidence viewer, Support Assessment, review queue/actions, audit timeline, feedback, safe async/error states.

**Expected files/modules:** `apps/web/src/routes`, `features/claims`, `features/evidence`, `features/reviews`, `features/operations`, `components`, `api`, accessibility tests.

**Acceptance criteria:** Authoritative vs generated/stale states explicit; citations open exact source; contradictions side-by-side; severity not color-only; no raw generated HTML; keyboard-complete workflows; responsive enterprise layout.

**Tests required:** Component states, contract mocks, Playwright adjuster/reviewer journeys, axe, keyboard/focus, screen-reader smoke, XSS content, SSE reconnect/conflict recovery.

**Dependencies:** M9 APIs; may develop against contracts after M1.

**Risks:** Chat-centric drift, information overload, inaccessible dense panels, frontend security assumptions.

**Definition of done:** Persona usability scripts and WCAG 2.2 AA target checks pass with recorded evidence; UI never implies AI approval authority.

## Milestone 11 — Evaluation and operations productization

**Objective:** Make quality, cost, latency, feedback, and regressions visible and release-blocking.

**Components:** Dataset registry, evaluation runner/results, deterministic evaluators, calibrated judge interface, comparison/gates, operations dashboards, alert definitions, failure harvesting.

**Expected files/modules:** `packages/evaluation`, `data/golden`, evaluation APIs/workers, `infrastructure/observability`, dashboard/alert definitions, authorized Vue operations views.

**Acceptance criteria:** Immutable manifests; paired baseline comparison by slice; hard safety gates; metrics expose sample counts/versions; failure becomes synthetic regression case; content-minimized telemetry.

**Tests required:** Evaluator units, judge calibration fixture, gate logic, metric definitions, redaction, dashboard queries, alert simulations, end-to-end release comparison.

**Dependencies:** M3, M5–M10.

**Risks:** Metric gaming, golden leakage, uncalibrated judges, sensitive telemetry, alert fatigue.

**Definition of done:** A deliberately regressed candidate is blocked for the expected reason and an approved candidate produces a complete reproducible report and dashboard trail.

## Milestone 12 — AWS infrastructure and controlled deployment

**Objective:** Deploy the same contracts securely on the approved AWS baseline.

**Components:** Terraform modules/environments, VPC/endpoints, ALB/WAF, ECS/Fargate, ECR, S3, Aurora/RDS PostgreSQL, SQS/DLQ, EventBridge, IAM, KMS, Secrets Manager, Cognito/federation, CloudWatch, budgets, deployment pipeline.

**Expected files/modules:** `infrastructure/terraform/modules/*`, `environments/dev|staging|prod`, IAM policy tests, `.github/workflows/deploy.yml`, runbooks and architecture evidence.

**Acceptance criteria:** Private data plane; least-privilege task/deploy roles; encryption and backups; immutable promotion; budget/alarms; no static AWS CI keys; mock/local auth rejected; restore and rollback validated.

**Tests required:** Terraform validate/plan/policy, IAM negative tests, container/image scan, staging smoke/golden canary, load/failure, backup restore, DLQ redrive, key/secret rotation, deployment rollback.

**Dependencies:** M0–M11, though nonproduction modules can begin earlier after contracts stabilize.

**Risks:** IAM complexity, regional Bedrock/model access, quotas, network cost, unsafe migrations, cost overrun.

**Definition of done:** Staging deployment passes operational-readiness checklist and production-like canary using only synthetic data; achieved—not merely target—RPO/RTO and performance are recorded.

## Milestone 13 — Optional evidence-driven spikes

**Objective:** Evaluate optional technologies without contaminating the main architecture.

**Components:** Separate spikes for Strands, AgentCore, OpenSearch, Textract, or SageMaker, each using existing ports and the same golden cases.

**Expected files/modules:** `experiments/<technology>`, isolated Terraform module, experiment manifest/report, ADR amendment or superseding ADR.

**Acceptance criteria:** Written hypothesis, simpler baseline, representative benchmark, security/threat update, cost cap, exit/adoption thresholds, and removal path.

**Tests required:** Contract parity, quality/latency/cost comparison, authorization and failure tests, teardown verification.

**Dependencies:** Relevant stable interface and baseline from M4–M12.

**Risks:** Technology-showcase bias, unreproducible vendor comparison, orphaned paid resources.

**Definition of done:** Evidence supports adopt/reject/defer; rejected spike is fully removed; adoption uses a reviewed ADR and does not break local/CI operation.

## Program-level completion

The reference release is done only when all required scenario classes execute through the polished UI, evidence/citation/support/review behavior matches the frozen golden dataset, offline CI is green, AWS staging is reproducible from Terraform, security and recovery exercises pass, telemetry reconstructs every workflow, and documentation reflects the deployed architecture. A visually successful demo without these properties is not complete.
