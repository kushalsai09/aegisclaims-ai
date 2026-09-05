# Phase 5 Model-Assistance Operations

Local and CI execution defaults to `MODEL_PROVIDER=deterministic`; no credentials or network are required. `MODEL_TIMEOUT_SECONDS` and `MODEL_MAX_RETRIES` are bounded configuration values. The deterministic provider is rejected outside local/test environments.

Operational diagnosis should use correlation IDs and the `model_invocations` metadata. Do not log prompts, document bodies, secrets, or credentials. Rejected outputs record reason codes such as malformed output, unauthorized citation, wrong-policy citation, prohibited output, or provider unavailability.

OpenTelemetry spans cover retrieval, model invocation, and validation. Existing HTTP and SQL spans cover API, persistence, and workflow integration. A failed model call is isolated from Phase 1–4 paths and never creates a user-visible brief.

For local verification, start Compose, run `scripts/phase5-smoke-test.sh`, then run the Phase 5 evaluation with a host-resolvable `DATABASE_URL` when invoked outside the containers.
