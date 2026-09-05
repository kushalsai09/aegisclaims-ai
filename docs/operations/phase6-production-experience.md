# Phase 6 Operations

## Authentication troubleshooting

Confirm migration head `20260826_0006`, rerun the idempotent seed, and verify that the account is active. Invalid credentials intentionally return one generic response; disabled accounts return an explicit disabled state. Session records can be inspected by authorized database operators without exposing the raw cookie token. Logout and expiry are irreversible for that session.

## Model-provider operation

Deterministic mode is the safe local default. Bedrock opt-in requires `MODEL_PROVIDER=bedrock`, an approved `BEDROCK_MODEL_ID`, `BEDROCK_REGION`, AWS credentials supplied through the runtime credential chain, and `bedrock:InvokeModel`. Absence of any required nonsecret setting fails startup. Provider failure never blocks claim evidence, document access, or human workflows.

Controls include a 30,000-character evidence-context ceiling, 1,200-token output ceiling, eight-second timeout, and one application retry by default. Provider-reported usage is recorded when available; no fake cost is calculated. Metrics cover invocation outcomes, latency, validation failures, provider timeouts/throttling/failures/retries, token usage, and human-review routing without prompt or document content.

## Verification

Run authentication and Phase 6 smoke tests against the Compose web URL. Run the deterministic adversarial evaluation on every release. Run the live Bedrock test only in an approved environment; a skip means NOT CONFIGURED, not passed.
