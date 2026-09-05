# Evaluation Strategy

## Purpose

Evaluation is a product subsystem and release discipline, not a final test phase. Every model, prompt, extraction, retrieval, rule, graph, and support-assessment change is evaluated against immutable synthetic cases before promotion and monitored after release.

See [evaluation pipeline](../diagrams/08-evaluation-pipeline.mmd).

## Layers

### Data and ingestion

Measure file acceptance correctness, extraction text/layout fidelity, document classification precision/recall/F1 with abstentions, chunk provenance validity, and index completeness. OCR/noise cases are a separate slice.

### Retrieval

Measure recall@k, precision@k where labels are exhaustive, MRR, nDCG@k, governing-policy-version accuracy, metadata/authorization violations, duplicate rate, and latency. Report by scenario and query class.

### Generation

Measure schema validity, claim/fact correctness, groundedness/faithfulness, assertion-level citation coverage and validity, required-element completeness, abstention correctness, prohibited-action rate, and concise rationale usefulness.

### Rules and Support Assessment

Use deterministic expected results for required fields, policy applicability, contradictions, rule outcomes, signal construction, risk category, and escalation reason codes. Assess escalation recall and precision by risk class; safety-critical mandatory cases prioritize recall.

### Agent/workflow

Measure expected node path, tool selection, tool argument validity, unauthorized/unnecessary calls, retry behavior, interrupt/resume correctness, terminal status, idempotency, and task completion.

### System and business

Measure end-to-end and stage latency, error/retry rate, throughput, availability, token/cost estimates, review rate, time to review, employee edit distance, usefulness, issue-discovery rate, and estimated manual time saved. Business metrics require a declared measurement method and cannot be claimed from synthetic benchmarks alone.

## Evaluator hierarchy

1. Referential and deterministic checks wherever possible.
2. Human-labelled expected values and rubric review.
3. Traditional similarity/classification metrics when valid for the task.
4. LLM-as-judge only for semantic properties lacking adequate deterministic tests.

Judge use requires a versioned rubric, blinded candidate identity, structured output, multiple examples, calibration against human labels, disagreement tracking, and no sole authority over safety-critical release gates.

## Run manifest

Each run freezes code commit, dataset/case versions, graph, prompts, schemas, model policy/provider/model, extraction/chunking/embedding/index/fusion/reranker versions, rule set, evaluator versions, environment, seeds, budgets, and timestamps. Result artifacts are immutable and comparable to an approved baseline.

## Release gates

- No safety-critical deterministic regression.
- No cross-tenant/metadata-filter or invalid governing-version evidence.
- Mandatory-review cases must escalate as expected.
- Citation referential validity must meet the declared task threshold, with zero tolerance for fabricated source IDs.
- Quality slices cannot be hidden by aggregate improvement.
- Latency and estimated cost must remain within approved budgets or receive explicit acceptance.
- Statistical uncertainty and sample size accompany comparisons; a tiny benchmark does not justify broad claims.

Exact thresholds are established after the baseline dataset and threat cases are reviewed. They belong in a versioned evaluation policy, not hard-coded into documentation.

## Online evaluation

Production-like monitoring samples eligible synthetic/demo requests or appropriately governed production requests. Deterministic checks can run synchronously; expensive judges run asynchronously on minimized, authorized data. Alerts compare rolling metrics and versions. User feedback is a signal, not ground truth, and is protected against duplicate or adversarial weighting.

## Human review program

Use a rubric, trained reviewers, double-review sample, adjudication for disagreements, inter-rater agreement, and documented sampling. Reviewers see evidence and task instructions but are blinded to candidate identity where feasible. Findings become new regression cases after privacy and provenance review.
