# ADR-009: Deterministic Rules versus LLM Reasoning

- **Status:** Accepted
- **Decision date:** 2026-08-26

## Context

Some tasks are exact—date applicability, required-field presence, permissions, thresholds, schema/citation validity—while others require language understanding. Asking a model to perform both reduces reproducibility and explainability.

## Decision

Use deterministic code/data rules for exact logic and LLMs for bounded extraction, semantic comparison, synthesis, and drafting. Rule inputs/outputs are typed, versioned, evidence-linked, and tested. Demonstration domain rules are labelled **SYNTHETIC DEMONSTRATION RULE**. Models cannot override rule outcomes.

## Alternatives

- **LLM for all reasoning:** simpler prompt surface but nondeterministic and difficult to audit.
- **Rules for all language:** reproducible but brittle and expensive to author for varied text.
- **External enterprise rule engine now:** powerful authoring/governance, unjustified initial complexity.

## Trade-offs and consequences

Hybrid design requires routing and normalized facts. It makes failure modes observable and tests focused. Conflicting semantic and deterministic results become an issue or review trigger rather than implicit precedence.

## Success criteria

100% deterministic golden results for exact rules; explicit provenance/version for each result; semantic tasks outperform simple baselines; no prompt change alters a deterministic permission, applicability, or escalation rule.
