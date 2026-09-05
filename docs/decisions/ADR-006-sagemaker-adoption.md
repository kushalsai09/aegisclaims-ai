# ADR-006: SageMaker Adoption Strategy

- **Status:** Accepted
- **Decision date:** 2026-08-26

## Context

SageMaker is valuable for trained/hosted ML, but the reference workflow can begin with deterministic logic, retrieval, managed embeddings, and LLM tasks. Adding it without a validated model problem would create cost and MLOps ceremony.

## Decision

Do not include SageMaker in the initial runtime. Preserve an `MLInferencePort` and experiment metadata compatible with a future document classifier, risk-prioritization model, anomaly detector, or reranker. Adopt only after a labelled dataset, baseline, measurable lift, and serving requirement exist.

## Alternatives

- **SageMaker immediately:** demonstrates MLOps but lacks a legitimate target and baseline.
- **In-process scikit-learn model:** suitable for small deterministic baselines; limited managed scaling/registry.
- **Bedrock/LLM task:** fast for language problems but may be costlier or less stable than a trained narrow model.

## Trade-offs and consequences

Deferral means the portfolio initially demonstrates evaluation/MLOps concepts through prompts, retrieval, and data artifacts rather than a trained endpoint. A later candidate must compare simple heuristic, in-process model, LLM, and SageMaker-hosted options.

## Success criteria

Adopt only if held-out quality, calibration/abstention, latency, cost, explainability, monitoring, and operational burden meet an approved threshold and beat the simpler baseline. Drift and retraining must be meaningful for the selected target, not generic dashboard decoration.
