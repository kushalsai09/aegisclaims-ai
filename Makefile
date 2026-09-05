.PHONY: bootstrap dev down logs migrate seed test test-backend test-frontend lint format typecheck check smoke compose-check

bootstrap:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -e '.[dev]'
	npm install

dev:
	docker compose -f infrastructure/docker/compose.yaml up --build -d

down:
	docker compose -f infrastructure/docker/compose.yaml down

logs:
	docker compose -f infrastructure/docker/compose.yaml logs -f api worker web

migrate:
	.venv/bin/alembic upgrade head

seed:
	.venv/bin/python -m insurance_platform.seed

test: test-backend test-frontend

test-backend:
	.venv/bin/pytest --cov=insurance_platform --cov-report=term-missing

test-frontend:
	npm run test

lint:
	.venv/bin/ruff check .
	npm run lint

format:
	.venv/bin/ruff format .
	npm run format --workspace @insurance-ops/web

typecheck:
	.venv/bin/mypy packages/backend/src
	npm run typecheck

check: lint typecheck test build

build:
	npm run build

smoke:
	./scripts/smoke-test.sh

compose-check:
	docker compose -f infrastructure/docker/compose.yaml config --quiet
