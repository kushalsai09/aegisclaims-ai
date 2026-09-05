import pytest
from fastapi.testclient import TestClient


def test_liveness_returns_version_and_correlation_id(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Correlation-ID": "test-correlation"})
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.1.0",
        "environment": "test",
        "checks": None,
    }
    assert response.headers["X-Correlation-ID"] == "test-correlation"


def test_readiness_checks_all_local_dependencies(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["checks"] == {
        "database": "ready",
        "object_storage": "ready",
        "queue": "ready",
    }


def test_readiness_returns_503_when_a_dependency_is_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def unavailable() -> bool:
        return False

    monkeypatch.setattr(client.app.state.components.object_storage, "healthcheck", unavailable)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["object_storage"] == "unavailable"


def test_readiness_sanitizes_dependency_exceptions(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def failed_healthcheck() -> bool:
        raise RuntimeError("redis://user:secret@internal-host")

    monkeypatch.setattr(client.app.state.components.job_queue, "healthcheck", failed_healthcheck)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["queue"] == "unavailable"
    assert "secret" not in response.text


def test_openapi_uses_versioned_application_routes(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    assert "/api/v1/claims" in document["paths"]
    assert document["info"]["version"] == "0.1.0"
