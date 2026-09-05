# Contributing

Use small reviewed changes, preserve the decision-support boundary, and never add real PII or proprietary carrier material. New synthetic domain thresholds must be labelled **SYNTHETIC DEMONSTRATION RULE**.

Before opening a pull request, run `make lint`, `make typecheck`, `make test`, `make build`, and `make compose-check`. Architecture changes require an ADR. Provider credentials, prompts containing secrets, unrestricted document content in telemetry, and generated lockfile changes without the matching manifest change are prohibited.
