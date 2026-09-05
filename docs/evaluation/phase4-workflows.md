# Phase 4 Workflow Evaluation

The executable harness reads `data/golden/phase4-workflows.json` and runs all ten fictional HarborView scenarios through the real workflow service. Rules in the corpus remain visibly labeled **SYNTHETIC DEMONSTRATION RULE**.

Metrics and thresholds are deterministic:

- state accuracy: 1.00
- human-review accuracy: 1.00
- citation integrity: 1.00
- signal accuracy: 1.00
- idempotency accuracy: 1.00
- forbidden autonomous-action rate: 0
- cross-tenant/cross-claim citation violations: 0

Run `scripts/phase4-evaluate.sh` against a migrated, seeded database. A nonzero exit means at least one scenario, safety target, citation, or isolation assertion failed. The harness does not invent model-quality metrics: it evaluates the local deterministic implementation actually executed.

