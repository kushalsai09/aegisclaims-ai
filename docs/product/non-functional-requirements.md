# Non-Functional Requirements

Initial values are engineering objectives to validate during implementation, not claims of achieved performance.

## Reliability and consistency

- **NFR-001:** API availability target for the portfolio production environment is 99.9% monthly, excluding declared maintenance.
- **NFR-002:** Workflow commands, queue handlers, and review creation must be idempotent. At-least-once delivery must not duplicate externally visible state.
- **NFR-003:** A process restart must not lose an accepted upload, completed workflow checkpoint, audit event, or human decision.
- **NFR-004:** Dependency calls must have explicit connect/read deadlines, bounded exponential backoff with jitter, and non-retryable error classification.
- **NFR-005:** Degraded dependencies must produce a visible partial/failed state rather than a fabricated complete answer.

## Performance and scale

- **NFR-010:** Read-only claim APIs should meet p95 under 500 ms at the documented reference load, excluding bulk document bodies.
- **NFR-011:** Workflow start acknowledgement should meet p95 under 1 second; analysis runs asynchronously with per-stage latency budgets.
- **NFR-012:** Retrieval should meet p95 under 1.5 seconds for the initial corpus and declared `k`, measured separately from generation.
- **NFR-013:** Load tests must define dataset size, concurrency, hardware, warm/cold state, and pass thresholds; no unqualified scale claims are allowed.

## Security and privacy

- **NFR-020:** All network traffic uses TLS; production data is encrypted at rest with managed keys and explicit key policies.
- **NFR-021:** Authorization defaults to deny and is tested for horizontal and vertical privilege escalation.
- **NFR-022:** Secrets never enter source control, images, prompts, logs, traces, fixtures, or frontend bundles.
- **NFR-023:** Original documents are immutable; derived artifacts are versioned and deletions follow an explicit retention workflow.
- **NFR-024:** Logs and evaluation datasets minimize sensitive content; access to full evidence is separately authorized and audited.

## AI quality and safety

- **NFR-030:** All production AI outputs use versioned schemas and fail closed on validation errors.
- **NFR-031:** Every displayed grounded assertion must map to at least one validated evidence span or be explicitly identified as employee-provided or unresolved.
- **NFR-032:** Golden-set release thresholds are defined before model/prompt/retrieval changes can deploy.
- **NFR-033:** Prompt-injection and tool-authorization adversarial tests are blocking CI or preproduction gates.
- **NFR-034:** The deterministic mock provider produces stable outputs across CI runs.

## Audit and observability

- **NFR-040:** A correlation ID links ingress, workflow, retrieval, model, tool, review, evaluation, and audit records.
- **NFR-041:** Audit events are append-only, time-ordered, actor-attributed, schema-versioned, and integrity-verifiable.
- **NFR-042:** Metrics include request volume, latency, errors, retrieval quality, model use, token/cost estimates, review rates, and evaluation regressions.
- **NFR-043:** Telemetry must not capture private chain-of-thought or unrestricted document contents.

## Maintainability and delivery

- **NFR-050:** Python is formatted, linted, type-checked, dependency-scanned, and tested in CI; TypeScript receives equivalent lint, type, unit, and build checks.
- **NFR-051:** APIs, events, prompts, schemas, graphs, rules, datasets, and infrastructure are version-controlled.
- **NFR-052:** Local development and CI require no paid API credential.
- **NFR-053:** Infrastructure changes use reviewed Terraform plans and environment promotion.

## Accessibility and interoperability

- **NFR-060:** The primary UI targets WCAG 2.2 AA and is tested with automated checks plus keyboard and screen-reader scenarios.
- **NFR-061:** Public internal contracts use documented JSON/OpenAPI schemas and stable UTC/UUID conventions.

## Recovery and cost

- **NFR-070:** Initial targets are RPO 15 minutes and RTO 4 hours for the portfolio production environment; restore tests must validate them before they are advertised as achieved.
- **NFR-071:** Every model invocation records estimated cost from a versioned price table and enforces per-workflow token/call budgets.
- **NFR-072:** Nonproduction environments support scheduled scale-down and budget alerts.
