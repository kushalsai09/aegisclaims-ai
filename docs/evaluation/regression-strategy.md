# Regression Strategy

## Test pyramid

1. **Per change:** formatting, lint, type checks, schema/contract tests, domain/rule units, authorization properties, deterministic mock graph cases, prompt-injection cases, and a fast golden subset.
2. **Pull request:** integration tests for PostgreSQL/pgvector/object/queue adapters, full deterministic golden suite, retrieval benchmark on a fixed index, frontend accessibility and critical E2E paths.
3. **Scheduled or release candidate:** paid-provider candidates, full retrieval/generation/agent benchmarks, calibrated judges, load/failure tests, dependency/IaC/container scans, and restore exercises as appropriate.
4. **Post-deploy:** smoke, canary synthetic journeys, online deterministic checks, and version-stratified monitoring.

## Baselines

A baseline is an immutable manifest plus results approved for a dataset version. Candidate comparisons use the same dataset, index snapshot, evaluator versions, and budgets unless the experiment explicitly studies one of those factors. Paired per-case deltas are preferred over comparing aggregate runs with different samples.

## Gating policy

- Hard gate: authorization violation, fabricated citation ID, invalid policy applicability presented as governing, failed mandatory escalation, prohibited autonomous decision, unsafe tool authorization, or deterministic rule/schema regression.
- Quality gate: lower confidence bound or configured slice threshold for retrieval/generation/task metrics.
- Operational gate: latency, error, retry, and cost budget.
- Review gate: material evaluator disagreement or new failure class requires human adjudication.

Thresholds are versioned after a baseline; waivers require owner, rationale, expiry, risk, and follow-up case. Averages cannot waive a safety-critical slice failure.

## Flake and nondeterminism

Mock tests must be deterministic. Paid-model tests record seeds/settings where supported, use repeated runs for unstable tasks, and distinguish provider variance from product regression. A flaky test is quarantined only with an owner and expiry; its safety coverage must be replaced before removal from a release gate.

## Model/prompt/retrieval promotion

1. Register candidate versions.
2. Run offline suite and compare paired metrics/slices.
3. Human-review disagreements and safety cases.
4. Approve immutable release manifest.
5. Deploy to staging and run synthetic canary.
6. Production canary by allowed traffic/configuration.
7. Monitor and automatically or manually roll back to the prior manifest when gates breach.

Rollback changes configuration to a known compatible manifest; database and graph-state compatibility are checked before deployment. In-flight runs retain the version set they began with.

## Failure harvesting

Authorized user feedback, incidents, abstentions, review edits, invalid outputs, and retrieval misses enter a triage queue. After privacy/provenance review, each distinct defect gets a minimized synthetic reproduction, expected behavior, regression test, and taxonomy tag.
