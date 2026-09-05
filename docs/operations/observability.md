# Observability

## Objective

For an authorized investigation, the platform must reconstruct what request occurred, which workflow path ran, which tools and evidence were used, which configuration versions produced the artifact, what it cost, how long it took, what failed, which evaluations applied, and how humans acted—without recording private chain-of-thought or indiscriminately copying documents.

See [observability flow](../diagrams/10-observability-flow.mmd).

## Telemetry architecture

OpenTelemetry is the instrumentation contract for traces, metrics, and structured logs. Local Compose exports to an OpenTelemetry Collector and local backends. AWS exports through a Collector/ADOT-compatible path to CloudWatch and X-Ray-compatible trace views as selected. Audit events use a separate durable application channel.

Phase 7 currently instruments HTTP route templates, SQLAlchemy, authentication,
rate limiting, worker failures, retrieval, workflows, and model invocation.
Queue depth/age, DLQ, outbox, currency cost, and X-Ray export are target signals,
not implemented metrics. The Terraform requires an externally operated private
OTLP/HTTP collector endpoint and does not claim to create that backend.

## Correlation and version context

Every ingress receives a correlation/trace ID. Spans and events carry safe identifiers for tenant, user/workload actor, claim, workflow run, node, job, retrieval run, model invocation, review task, and evaluation run. They also carry graph, prompt, schema, rule, retrieval, index, embedding, model policy/provider/model, and application release versions.

High-cardinality identifiers belong in traces/logs, not metric labels. Metrics use bounded dimensions such as environment, task, provider, model policy, graph node, outcome, scenario/risk category, and version family.

## Signals

### Traces

Ingress, authorization decision, database transaction, outbox publish, queue wait/consume, graph node, retrieval stages, reranking, prompt preparation, model call, output validation, tool call, rule evaluation, review interrupt/resume, audit write, and response/event delivery.

Trace attributes store counts, hashes/references, statuses, timing, usage, and reason codes. Full prompts, chain-of-thought, bearer tokens, secrets, unrestricted source text, and full model responses are excluded by default.

### Metrics

Request/job volume; latency percentiles; errors, retries, timeouts, throttles, circuit state; queue depth/age/DLQ; database saturation; retrieval quality/latency; schema and citation validity; abstain/review/escalation rates; graph/tool failures; tokens and estimated cost; evaluation/regression status; human-review time/outcome; telemetry and audit health.

### Logs

JSON logs include timestamp, severity, stable event code, safe message, correlation, component, outcome, and error classification. Error details are sanitized. Sampling never drops security, audit, review, or terminal failure events.

### Audit

Audit is append-only domain evidence, not a debug log. It records access and consequential changes with actor, reason, before/after references, versions, and integrity linkage. Audit ingestion failure blocks configured high-value state transitions.

## Dashboards

- Executive service health: volume, success/partial/review/failure, latency, cost.
- AI quality: retrieval, citations, groundedness, abstention, scenario slices, versions.
- Workflow: node latency/error, path distribution, interrupts, retries, DLQs.
- Human review: queue age, reasons, outcomes, stale tasks, time to decision.
- Security: access denials, injection indicators, blocked tools, validation failures.
- Data/index: ingestion status, extraction failures, index lag, reconciliation.
- Release comparison: baseline/candidate and pre/post-deploy regression signals.

## Alerts and SLOs

Alerts must be actionable and route to an owner/runbook. Candidates include sustained API error/latency burn, oldest queue age, DLQ message, audit write failure, authorization anomaly, cross-scope retrieval violation, citation validity breach, mandatory-escalation failure, cost anomaly, model throttling, and index staleness. Initial SLO objectives are validated under load before being presented as achieved.

## Retention and access

Telemetry classes have explicit retention and access roles. Operations reviewers receive aggregated views by default; claim-level traces require purpose-bound access. Redaction tests run in CI. Content needed for a reproducible evaluation is stored as a governed artifact reference rather than embedded repeatedly in telemetry.
