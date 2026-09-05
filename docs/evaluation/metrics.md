# Metrics Catalog

## Metric rules

Every metric has an owner, definition, numerator/denominator, unit, dimensions, source, refresh cadence, target/gate, and limitations. Dashboards must display sample count and time/version filters. Means alone are insufficient for skewed latency/cost; use percentiles and distributions.

## Retrieval

- `recall_at_k`: relevant governing items retrieved divided by annotated relevant items.
- `precision_at_k`: relevant items among top k; only valid when relevance labels are sufficiently complete.
- `mrr`: reciprocal rank of first relevant item.
- `ndcg_at_k`: graded ranking quality.
- `policy_version_accuracy`: queries whose selected governing evidence has correct policy/edition/effective period.
- `metadata_scope_violation_count`: evidence outside authorized tenant/resource/applicability filters; release tolerance is zero.
- `duplicate_evidence_rate`: redundant results among selected evidence.
- `retrieval_latency_ms`: p50/p95/p99 by backend/config/query class.

## Extraction and generation

- Document classification macro/micro precision, recall, F1, and abstention accuracy.
- Fact field precision/recall/F1 with exact/normalized value and provenance checks.
- Structured-output validity rate before and after bounded syntax repair.
- Assertion correctness and evidence-groundedness.
- Citation coverage: supported assertions with citations / assertions requiring evidence.
- Citation referential validity: cited IDs/spans that exist and belong to snapshot.
- Citation entailment: evidence supports the associated proposition, using human or calibrated semantic evaluation.
- Completeness by required proposition/rubric element.
- Correct abstention rate and unsupported-answer rate.
- Prohibited-action or prohibited-conclusion rate.

## Rules, support, and workflow

- Rule exact-match rate and branch coverage.
- Required-field completeness exact match.
- Contradiction precision/recall by materiality/type.
- Escalation recall/precision by reason and risk category.
- Expected-path match, task completion, and terminal-state correctness.
- Tool-selection precision/recall, invalid argument rate, unauthorized call count, and unnecessary call rate.
- Interrupt/resume success, stale-review rejection, duplicate task count, and idempotent replay consistency.

## Operational

- Request/job volume and concurrency.
- API and per-node p50/p95/p99 latency.
- Success, partial, abstain, review, retry, failure, timeout, and DLQ rates.
- Provider/model calls, input/output tokens, cache use, throttles, and estimated cost.
- Estimated cost per request, workflow, successful supported artifact, and evaluation run.
- Queue age/depth, worker utilization, database pool/saturation, and index freshness.
- Trace/audit completeness and telemetry export failure rate.

## Human and business-oriented

- Review rate and reason distribution.
- Time to assignment/decision and returned-for-more-evidence rate.
- Employee usefulness rating with response count.
- Employee edit rate and semantic/structured correction categories.
- Evidence issues discovered before human decision.
- Estimated task-time reduction from controlled usability studies.

Synthetic results demonstrate system behavior, not real-world business impact. Business claims require a designed study, baseline, representative users/tasks, and uncertainty reporting.

## Cost calculation

Use a versioned price catalog keyed by provider/model/region/effective date and actual usage where available. Label estimates when provider billing units are incomplete. Infrastructure allocation methodology is documented separately from marginal model cost.
