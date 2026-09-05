from __future__ import annotations

import os
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, inspect, text


@pytest.mark.integration
def test_alembic_migration_on_postgresql() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for the PostgreSQL migration integration test")
    environment = os.environ.copy()
    environment.update(
        {
            "APP_ENV": "test",
            "DATABASE_URL": database_url,
            "AUTH_PROVIDER": "local",
            "DEV_AUTH_SECRET": "integration-test-secret-with-at-least-thirty-two-characters",
            "OBJECT_STORAGE_PROVIDER": "memory",
            "QUEUE_PROVIDER": "memory",
        }
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], check=True, env=environment
    )
    subprocess.run([sys.executable, "-m", "insurance_platform.seed"], check=True, env=environment)
    subprocess.run([sys.executable, "-m", "insurance_platform.seed"], check=True, env=environment)
    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert {
        "users",
        "roles",
        "claims",
        "policies",
        "documents",
        "workflow_runs",
        "human_review_tasks",
        "audit_events",
        "document_indexes",
        "retrieval_chunks",
        "workflow_checkpoints",
        "workflow_events",
        "review_artifacts",
        "workflow_review_actions",
        "model_invocations",
        "claim_evidence_briefs",
        "user_sessions",
        "oidc_login_transactions",
    }.issubset(tables)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM claims")) == 10
        assert connection.scalar(text("SELECT count(*) FROM documents")) == 15
        assert connection.scalar(text("SELECT count(*) FROM document_indexes")) == 15
        assert connection.scalar(text("SELECT count(*) FROM retrieval_chunks")) == 15
    engine.dispose()

    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "20260826_0006"],
        check=True,
        env=environment,
    )
    downgraded_engine = create_engine(database_url)
    assert "oidc_login_transactions" not in set(inspect(downgraded_engine).get_table_names())
    downgraded_engine.dispose()
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], check=True, env=environment
    )
    upgraded_engine = create_engine(database_url)
    assert "oidc_login_transactions" in set(inspect(upgraded_engine).get_table_names())
    upgraded_engine.dispose()
