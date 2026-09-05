import pytest
from fastapi.testclient import TestClient

from conftest import sign_in


@pytest.mark.system
def test_identity_to_api_to_database_smoke(client: TestClient) -> None:
    headers = sign_in(client, "claims_adjuster")
    dashboard = client.get("/api/v1/dashboard", headers=headers)
    claims = client.get("/api/v1/claims", headers=headers)
    workspace = client.get(f"/api/v1/claims/{claims.json()[0]['id']}", headers=headers)

    assert dashboard.json()["assigned_claims"] == 1
    assert workspace.json()["policy"]["edition"] == "2026-SYN-A"
    assert workspace.json()["workflow"]["status"] == "not_started"
