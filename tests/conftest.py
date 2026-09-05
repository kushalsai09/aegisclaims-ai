from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from insurance_platform.config import Environment, QueueProvider, Settings, StorageProvider
from insurance_platform.delivery.api import create_app
from insurance_platform.delivery.components import build_components
from insurance_platform.infrastructure.database import Base
from insurance_platform.seed import seed


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        app_env=Environment.TEST,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'test.db'}",
        auth_provider="local",
        dev_auth_secret="test-local-secret-with-at-least-thirty-two-characters",
        object_storage_provider=StorageProvider.MEMORY,
        queue_provider=QueueProvider.MEMORY,
        otel_enabled=False,
    )


@pytest.fixture
def client(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    components = build_components(settings)
    Base.metadata.create_all(components.engine)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", settings.database_url)
    monkeypatch.setenv("AUTH_PROVIDER", "local")
    monkeypatch.setenv("DEV_AUTH_SECRET", "test-local-secret-with-at-least-thirty-two-characters")
    monkeypatch.setenv("OBJECT_STORAGE_PROVIDER", "memory")
    monkeypatch.setenv("QUEUE_PROVIDER", "memory")
    seed(components.session_factory)
    app = create_app(settings=settings, components=components)
    with TestClient(app) as test_client:
        yield test_client
    components.engine.dispose()


def sign_in(client: TestClient, role: str) -> dict[str, str]:
    users = client.get("/api/v1/auth/dev/users").json()
    user = next(user for user in users if role in user["roles"])
    response = client.post("/api/v1/auth/dev/session", json={"user_id": user["id"]})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
