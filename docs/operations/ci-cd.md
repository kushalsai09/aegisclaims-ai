# CI/CD Strategy

## Goals

Produce reproducible, scanned, evaluated, immutable artifacts; promote the same artifact through environments; use short-lived deployment identity; and prevent application, AI configuration, schema, or infrastructure regressions.

See [CI/CD diagram](../diagrams/09-ci-cd.mmd).

## Pull-request pipeline

The checked Phase 7 workflow executes Python and frontend lint/type/test/build,
PostgreSQL migration integration, coverage threshold, pip/npm dependency audit,
secret-pattern checks, Terraform format/init/validate, documentation links,
container builds, all seven phase smokes, and isolated database restore. Image
SBOM/signing, license policy, Terraform speculative plan, accessibility scanner,
container CVE scan, and cloud deployment are required future release gates and
must not be inferred from the current workflow.

1. Validate documentation links, Mermaid syntax, formatting, and ADR conventions.
2. Python format/lint/type/unit checks and dependency audit.
3. TypeScript format/lint/type/unit/build and accessibility component checks.
4. Generate/diff OpenAPI and event schemas; reject unapproved breaking changes.
5. Start ephemeral PostgreSQL/pgvector, object-store, and queue adapters for integration tests.
6. Run deterministic mock workflows, authorization/adversarial tests, and fast/full golden tiers according to change scope.
7. Scan secrets, source dependencies, licenses, Terraform, containers, and SBOM.
8. Terraform format/validate and speculative plan for nonproduction.

CI has no paid model credentials. Provider evaluations run in a protected scheduled/release workflow with budgets and explicit environment approval.

## Build and provenance

Build backend and frontend artifacts once from a pinned toolchain and lockfiles. Create minimal non-root images, SBOMs, vulnerability reports, commit/config provenance, and signatures/attestations. Push immutable digests to ECR. Never promote mutable `latest` tags.

AI assets—prompts, schemas, graph, rules, retrieval configuration, price catalog, and evaluation dataset manifest—are bound into or referenced by the release manifest with immutable versions.

## Deployment pipeline

1. Terraform plan with policy/security checks.
2. Human approval for protected environment and reviewed plan.
3. Apply backward-compatible infrastructure/database expansion.
4. Deploy artifact digest to staging.
5. Run health, contract, migration, synthetic end-to-end, accessibility smoke, and golden canary tests.
6. Approve production release manifest.
7. Deploy through rolling or blue/green strategy with canary synthetic checks.
8. Observe defined bake window and compare versions.
9. Roll back application/configuration on breach; complete contract migrations only after compatibility window.

## Branch and environment controls

Protected main branch, required review/status checks, CODEOWNERS for security/IaC/evaluation/rules, signed releases, restricted environment secrets, and GitHub Actions OIDC to AWS. Fork/untrusted workflows receive no secrets. Production apply and paid evaluation are separate permissions.

## Database and graph compatibility

Use expand/migrate/contract. A release must read the previous schema during rolling deployment. Destructive migration is deferred until old tasks and graph checkpoints are drained or migrated. In-flight workflows remain pinned to compatible graph/config versions.

## Rollback

Rollback selects a previously approved image digest and configuration manifest. Terraform rollback is not assumed safe; infrastructure changes use forward fixes or explicit reviewed recovery plans. Database down-migrations are avoided when data loss is possible.
