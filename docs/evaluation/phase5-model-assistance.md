# Phase 5 Model-Assistance Evaluation

The deterministic golden suite uses the same ten synthetic scenarios as Phase 3 and Phase 4. It measures structured-output validity, citation validity and coverage, state accuracy, review routing, injection-safety signals, wrong-policy and distractor citation rates, unsupported-claim rate, isolation violations, and prohibited autonomous-action rate.

Run `scripts/phase5-evaluate.sh`. Output is JSON and the process exits non-zero when any scenario or zero-tolerance safety metric fails. Each run uses unique idempotency keys so repeated evaluation is reproducible.

Evaluation invocations remain auditable. They do not alter retrieval authorization or workflow authority.
