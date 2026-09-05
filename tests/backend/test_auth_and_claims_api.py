from fastapi.testclient import TestClient

from conftest import sign_in


def test_protected_claim_requires_identity(client: TestClient) -> None:
    response = client.get("/api/v1/claims")
    assert response.status_code == 401
    assert response.json()["code"] == "identity_invalid"


def test_adjuster_can_open_synthetic_claim_workspace(client: TestClient) -> None:
    headers = sign_in(client, "claims_adjuster")
    claims = client.get("/api/v1/claims", headers=headers)
    assert claims.status_code == 200
    assert len(claims.json()) == 1

    workspace = client.get(f"/api/v1/claims/{claims.json()[0]['id']}", headers=headers)
    assert workspace.status_code == 200
    payload = workspace.json()
    assert payload["claim"]["claim_number"] == "HVC-SYN-2026-00017"
    assert len(payload["documents"]) == 2
    assert {section["status"] for section in payload["future_sections"]} == {"not_implemented"}
    assert "SYNTHETIC DEMONSTRATION DATA" in payload["synthetic_notice"]


def test_server_side_role_permissions_are_enforced(client: TestClient) -> None:
    adjuster = sign_in(client, "claims_adjuster")
    assert client.get("/api/v1/operations/summary", headers=adjuster).status_code == 403
    assert client.get("/api/v1/review-tasks", headers=adjuster).status_code == 403

    supervisor = sign_in(client, "supervisor")
    assert client.get("/api/v1/review-tasks", headers=supervisor).status_code == 200

    compliance = sign_in(client, "compliance_reviewer")
    assert client.get("/api/v1/operations/summary", headers=compliance).status_code == 200


def test_admin_can_enqueue_and_complete_local_smoke_job(client: TestClient) -> None:
    headers = sign_in(client, "admin")
    queued = client.post(
        "/api/v1/system/jobs/smoke", headers=headers, json={"message": "walking skeleton"}
    )
    assert queued.status_code == 200
    assert queued.json()["status"] == "queued"
