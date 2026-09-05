# AegisClaims AI - Governed Insurance Operations Platform

A production-oriented portfolio platform for internal insurance operations. The current implementation is **Phase 7: production readiness, cloud architecture, security, and resilience**. It retains the Phase 1–6 product and adds a real OIDC authorization-code/PKCE boundary, fail-closed production configuration, Redis-backed distributed rate limits, hardened containers and headers, bounded queries, operational telemetry, load/recovery/restore exercises, and a statically validated Terraform ECS/Fargate foundation. The Terraform has not been applied and live Bedrock is not claimed. The product contains no autonomous claim decisions, coverage authority, settlement recommendations, payment, fraud determination, external communication, or legal functionality.

All included people, policies, claims, documents, and rules are **SYNTHETIC DEMONSTRATION DATA**. This project does not represent any real insurer's data or internal systems.

## Local quick start

Prerequisites: Git, Docker with Compose v2, Python 3.12 or 3.13, and Node.js 22–24. Runtime containers currently pin Python 3.13.14 on Alpine 3.24, Node 24.4.1, and unprivileged Nginx 1.29.0 image tags; production promotion uses the resulting immutable digests.

```bash
cd /Users/kushal/Documents/dev
cp .env.example .env
docker compose -f infrastructure/docker/compose.yaml up -d --build
./scripts/wait-for-stack.sh
make smoke
```

Open:

- Employee application: <http://localhost:5173>
- API documentation: <http://localhost:8000/docs>
- Jaeger traces: <http://localhost:16686>
- MinIO console: <http://localhost:9001>

The local sign-in page uses fictional professional accounts. The shared development-only password is `HarborView!Local2026`; example email addresses are listed in the Phase 6 authentication documentation. Do not reuse these credentials outside local development.
The API entrypoint applies Alembic migrations and idempotently seeds the
synthetic portfolio before starting. The Compose API uses PostgreSQL, MinIO,
Redis, and the OpenTelemetry Collector; the worker consumes the Redis queue.
No edits are required after copying `.env.example`.

## Development without containers

Host mode is a separate configuration. Replace `.env` with the host template
when intentionally switching away from Compose:

```bash
make bootstrap
cp .env.host.example .env
mkdir -p .local
make migrate
make seed
```

Start the API in one terminal:

```bash
.venv/bin/uvicorn insurance_platform.delivery.api:create_app --factory --reload
```

Start the web application in another terminal:

```bash
npm run dev --workspace @insurance-ops/web
```

Then open <http://localhost:5173>. This host-only mode uses SQLite plus the
filesystem object-storage and in-memory queue adapters; it does not exercise PostgreSQL,
MinIO, Redis, or the separate worker process.

## Quality commands

```bash
make lint
make typecheck
make test
make build
make compose-check
```

Run the deterministic evaluations and Compose smoke tests:

```bash
./scripts/phase3-evaluate.sh
./scripts/phase4-evaluate.sh
./scripts/phase5-evaluate.sh
./scripts/phase6-evaluate.sh
./scripts/auth-smoke-test.sh
./scripts/phase2-smoke-test.sh
./scripts/phase3-smoke-test.sh
./scripts/phase4-smoke-test.sh
./scripts/phase5-smoke-test.sh
./scripts/phase6-smoke-test.sh
./scripts/phase7-smoke-test.sh
./scripts/phase7-load-test.sh smoke
./scripts/phase7-resilience-test.sh
./scripts/phase7-backup-restore-test.sh
```

The smoke scripts default to `http://localhost:5173`, where the containerized
Nginx service proxies `/api` to the Compose API. For intentional host-only API
testing, set `BASE_URL=http://localhost:8000` explicitly.

The local retrieval path uses deterministic 64-dimensional signed-token-hash
embeddings and a portable SQL chunk index. It performs lexical and vector
ranking followed by versioned reciprocal-rank fusion. No document is sent to
an external provider. PostgreSQL/pgvector remains the production direction
behind the retrieval port. The Compose PostgreSQL migration and pgvector
extension are validated, while pgvector-native similarity search remains a
documented future adapter; Phase 3 runtime retrieval uses the portable index.

Architecture, production prerequisites, incident procedures, and explicit cloud
limitations live in [docs](docs/README.md). Phase 8 is outside the current scope.
