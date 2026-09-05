# Phase 3 Retrieval Evaluation

The versioned corpus in `data/golden/phase3-retrieval.json` contains one
representative query for each of the ten synthetic scenario families. Each
query records expected and excluded documents, pages, evidence terms,
answerability, and the required structured answer state.

The executable harness reports Recall@3, Precision@3, MRR, correct-page rate,
wrong-policy/distractor exclusion, abstention accuracy, and isolation
violations. Failures name the scenario and observed evidence.

Acceptance thresholds are:

- Recall@3 at least 0.90, because missing governing evidence is a material
  grounding failure.
- Precision@3 at least 0.60, allowing limited corroborating evidence without
  tolerating distractor-dominated results.
- MRR at least 0.85, requiring relevant evidence near the top.
- Correct-page rate at least 0.90.
- Wrong-policy/distractor exclusion rate exactly 1.0 for annotated hard
  negatives.
- Abstention/state accuracy exactly 1.0 on this deterministic safety corpus.
- Zero cross-claim or cross-tenant isolation violations.

These thresholds are not claims about production quality. The corpus is small,
fully synthetic, and deterministic. A production release requires a larger,
independently reviewed benchmark plus validation of the future pgvector-native
retrieval adapter and any configured external generation provider. Phase 3
validated the live PostgreSQL migration and pgvector extension, not a
pgvector-native similarity-search adapter or external model provider.

Run the harness with:

```bash
./scripts/phase3-evaluate.sh
```
