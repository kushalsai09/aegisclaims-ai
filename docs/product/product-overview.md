# Product Overview

## Vision

The Enterprise AI Insurance Operations Platform is an internal employee decision-support system for document- and knowledge-intensive insurance work. Its first complete reference workflow, the Residential Property Claims Intelligence Copilot, assembles a synthetic claim, classifies and extracts its documents, retrieves the applicable fictional policy provisions, identifies missing or conflicting evidence, applies deterministic demonstration rules, drafts a cited summary, and routes uncertain or consequential work to a human.

The reference workflow proves reusable capabilities rather than defining the entire platform: identity and authorization, document ingestion, knowledge curation, hybrid retrieval, model access, workflow orchestration, human review, audit, evaluation, and observability. Later underwriting, policy intelligence, service knowledge, and compliance modules can reuse those services without inheriting claims-specific logic.

## Product principles

1. Employee accountability remains intact; AI output is advisory.
2. An answer without adequate evidence is an explicit unsupported result.
3. Deterministic rules handle deterministic questions.
4. Documents and retrieved text are untrusted inputs.
5. Evidence, versions, rule results, and workflow state are explainable; private chain-of-thought is never displayed or stored as a product feature.
6. Quality, latency, cost, security, and review behavior are measured from the first increment.
7. The local system remains useful and testable without paid services.

## Reference fictional product

The initial dataset models a fictional residential property policy called **HarborView HomeSecure HO-SYN-01**. It has versioned policy editions, endorsements, effective periods, coverages, exclusions, conditions, and required-evidence definitions. It is deliberately not a copy of any real carrier form.

Claims include structured loss data and synthetic artifacts such as a notice of loss, adjuster notes, homeowner statements, contractor estimates, receipts, inspection reports, photographs represented by metadata, correspondence, and policy documents. Variants exercise missing evidence, contradictions, ambiguous language, wrong policy versions, OCR noise, distractors, prompt injection, and unanswerable questions.

Where workflow logic requires a business threshold, the artifact must be labelled **SYNTHETIC DEMONSTRATION RULE** in source data, UI, documentation, and tests.

## Scope

### In the reference release

- Claim workspace and role-aware review queues.
- Structured claim and policy records with versioned synthetic documents.
- Document upload, validation, malware-scan integration point, extraction, classification, chunking, and indexing.
- Hybrid retrieval with metadata filtering, evidence citations, and optional reranking.
- Structured summary, fact extraction, missing-information detection, contradiction detection, policy evidence retrieval, and next-step drafting.
- Explainable Support Assessment and mandatory escalation rules.
- Human approve, reject, edit, return, and resume controls for decision-support artifacts.
- Audit history, feedback, evaluation runs, quality dashboards, cost and latency telemetry.

### Explicitly out of scope

- Autonomous coverage adjudication, payment, fraud accusation, legal advice, or customer communication.
- Production integration with a real carrier, real PII, real policies, or proprietary business rules.
- Multi-carrier tenancy administration in the first release.
- Training a foundation model, implementing every insurance product, or introducing optional AWS services without evidence.

## Outcome measures

The platform succeeds when benchmarked tasks show adequate retrieval recall, citation validity, structured-output validity, reliable escalation of unsupported/high-risk cases, reproducible audit records, acceptable latency/cost budgets, and positive reviewer usefulness ratings. It fails safely when a dependency, model, parser, or evidence requirement is unavailable.
