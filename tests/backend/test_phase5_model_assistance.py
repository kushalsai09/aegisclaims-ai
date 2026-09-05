from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from insurance_platform.evaluation.model_assistance import evaluate_model_assistance
from insurance_platform.infrastructure.models import (
    AuditEventModel,
    ClaimEvidenceBriefModel,
    ClaimModel,
    DocumentModel,
    ModelInvocationModel,
    PolicyModel,
    TenantModel,
)
from insurance_platform.model_assistance.provider import DeterministicBriefProvider
from insurance_platform.ports.model_provider import (
    ModelEvidence,
    ModelProviderError,
    ModelProviderTimeout,
    StructuredGenerationRequest,
)


def _headers(client: TestClient, role: str) -> dict[str, str]:
    users = client.get("/api/v1/auth/dev/users").json()
    user = next(item for item in users if role in item["roles"])
    session = client.post("/api/v1/auth/dev/session", json={"user_id": user["id"]}).json()
    return {"Authorization": f"Bearer {session['access_token']}"}


def _claim(client: TestClient, number: str) -> str:
    with client.app.state.components.session_factory() as session:
        claim = session.scalar(select(ClaimModel).where(ClaimModel.claim_number == number))
        assert claim is not None
        return str(claim.id)


def _create(client: TestClient, number: str, task: str, key: str) -> dict[str, object]:
    response = client.post(
        f"/api/v1/claims/{_claim(client, number)}/briefs",
        headers=_headers(client, "admin"),
        json={"task": task, "idempotency_key": key},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_provider_contract_success_timeout_failure_and_malformed() -> None:
    request = StructuredGenerationRequest(
        task="Summarize evidence",
        claim_number="HVC-1",
        applicable_policy_edition="2026-A",
        evidence=[ModelEvidence("CIT-1", "Supported evidence.", None, False)],
        correlation_id="test",
        prompt_template_version="v1",
        response_schema_version="v1",
    )
    assert (
        "supported"
        in DeterministicBriefProvider().generate_structured(request, timeout_seconds=1).content
    )
    assert (
        DeterministicBriefProvider("malformed")
        .generate_structured(request, timeout_seconds=1)
        .content
        == "not-json"
    )
    with pytest.raises(ModelProviderTimeout):
        DeterministicBriefProvider("timeout").generate_structured(request, timeout_seconds=1)
    with pytest.raises(ModelProviderError):
        DeterministicBriefProvider("failure").generate_structured(request, timeout_seconds=1)


def test_supported_brief_is_cited_audited_idempotent_and_workflow_linked(
    client: TestClient,
) -> None:
    claim_id = _claim(client, "HVC-SYN-2026-00017")
    headers = _headers(client, "admin")
    workflow = client.post(
        f"/api/v1/claims/{claim_id}/workflows",
        headers=headers,
        json={"task": "Review the loss evidence", "idempotency_key": "phase5-workflow-link"},
    ).json()
    body = {"task": "What loss date is supported?", "idempotency_key": "phase5-supported-001"}
    first = client.post(f"/api/v1/claims/{claim_id}/briefs", headers=headers, json=body)
    second = client.post(f"/api/v1/claims/{claim_id}/briefs", headers=headers, json=body)
    assert first.status_code == second.status_code == 201
    brief = first.json()
    assert brief["id"] == second.json()["id"]
    assert brief["workflow_id"] == workflow["id"]
    assert brief["status"] == "supported"
    assert brief["citations"] and all(item["claim_id"] == claim_id for item in brief["citations"])
    assert brief["provider"] == "local_deterministic"
    assert brief["authority_notice"].startswith("AI-assisted evidence brief")
    with client.app.state.components.session_factory() as session:
        invocation = session.scalar(
            select(ModelInvocationModel).where(ModelInvocationModel.id == uuid.UUID(brief["id"]))
        )
        assert invocation is None  # IDs intentionally identify different persisted concepts.
        assert session.scalar(select(func.count()).select_from(ModelInvocationModel)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditEventModel)
                .where(AuditEventModel.action == "model.brief.created")
            )
            == 1
        )


@pytest.mark.parametrize(
    ("number", "task", "expected", "signal"),
    [
        (
            "HVC-SYN-2026-00018",
            "What repair estimate amount is documented?",
            "insufficient_evidence",
            "missing_information",
        ),
        (
            "HVC-SYN-2026-00019",
            "What is the reported loss date?",
            "conflicting_evidence",
            "conflicts",
        ),
        (
            "HVC-SYN-2026-00020",
            "What caused the observed damage?",
            "ambiguous_evidence",
            "ambiguities",
        ),
        ("HVC-SYN-2026-00024", "What property address is documented?", "supported", "safety_flags"),
        (
            "HVC-SYN-2026-00025",
            "What caused the exterior condition?",
            "insufficient_evidence",
            "missing_information",
        ),
    ],
)
def test_deterministic_safety_scenarios(
    client: TestClient, number: str, task: str, expected: str, signal: str
) -> None:
    brief = _create(client, number, task, f"phase5-scenario-{number[-2:]}")
    assert brief["status"] == expected
    assert brief[signal]
    assert brief["human_review_required"] is True


@pytest.mark.parametrize(
    "behavior", ["malformed", "prohibited", "hallucinated_citation", "timeout", "failure"]
)
def test_unsafe_or_failed_provider_output_is_sanitized_and_never_persisted(
    client: TestClient, behavior: str
) -> None:
    client.app.state.components.model_provider = DeterministicBriefProvider(behavior)
    response = client.post(
        f"/api/v1/claims/{_claim(client, 'HVC-SYN-2026-00017')}/briefs",
        headers=_headers(client, "admin"),
        json={"task": "Summarize supported evidence", "idempotency_key": f"phase5-{behavior}"},
    )
    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "The model-assisted brief was rejected by application safety validation."
    )
    assert behavior not in response.text
    with client.app.state.components.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ClaimEvidenceBriefModel)) == 0
        invocation = session.scalar(select(ModelInvocationModel))
        assert invocation is not None and invocation.outcome == "rejected"


def test_brief_rbac_scope_and_stale_evidence(client: TestClient) -> None:
    claim_id = _claim(client, "HVC-SYN-2026-00024")
    body = {"task": "What address is documented?", "idempotency_key": "phase5-rbac-stale"}
    assert client.post(f"/api/v1/claims/{claim_id}/briefs", json=body).status_code == 401
    assert (
        client.post(
            f"/api/v1/claims/{claim_id}/briefs",
            headers=_headers(client, "compliance_reviewer"),
            json=body,
        ).status_code
        == 403
    )
    brief = client.post(
        f"/api/v1/claims/{claim_id}/briefs", headers=_headers(client, "admin"), json=body
    ).json()
    assert (
        client.get(f"/api/v1/briefs/{uuid.uuid4()}", headers=_headers(client, "admin")).status_code
        == 404
    )
    with client.app.state.components.session_factory() as session:
        document = session.scalar(
            select(DocumentModel).where(DocumentModel.claim_id == uuid.UUID(claim_id))
        )
        assert document is not None
        document.checksum_sha256 = "e" * 64
        session.commit()
    latest = client.get(
        f"/api/v1/claims/{claim_id}/briefs/latest", headers=_headers(client, "admin")
    )
    assert latest.status_code == 200
    assert latest.json()["id"] == brief["id"]
    assert latest.json()["stale"] is True
    assert latest.json()["validation_state"] == "stale"


def test_phase5_golden_evaluation_meets_all_safety_thresholds(client: TestClient) -> None:
    with client.app.state.components.session_factory() as session:
        result = evaluate_model_assistance(session)
    assert result.passed, result.failures
    assert result.structured_output_validity == 1.0
    assert result.citation_validity == 1.0
    assert result.citation_coverage == 1.0
    assert result.state_accuracy == 1.0
    assert result.human_review_routing_accuracy == 1.0
    assert result.safety_signal_accuracy == 1.0
    assert result.wrong_policy_citation_rate == 0
    assert result.distractor_citation_rate == 0
    assert result.unsupported_claim_rate == 0
    assert result.isolation_violation_count == 0
    assert result.prohibited_autonomous_action_rate == 0


def test_cross_tenant_brief_is_indistinguishable_from_missing(client: TestClient) -> None:
    tenant_id, policy_id, claim_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    with client.app.state.components.session_factory.begin() as session:
        session.add(TenantModel(id=tenant_id, name="Phase 5 Other Tenant"))
        session.add(
            PolicyModel(
                id=policy_id,
                tenant_id=tenant_id,
                policy_number="OTHER-P5",
                product_code="OTHER",
                product_name="Other Product",
                edition="2026-OTHER",
                effective_from=date(2026, 1, 1),
                effective_to=date(2027, 1, 1),
                status="active",
                synthetic_label="SYNTHETIC DATA",
            )
        )
        session.add(
            ClaimModel(
                id=claim_id,
                tenant_id=tenant_id,
                policy_id=policy_id,
                claim_number="OTHER-P5-CLAIM",
                loss_date=date(2026, 1, 2),
                loss_type="Other",
                property_address="Other Tenant",
                status="open",
                description="Cross-tenant Phase 5 fixture",
            )
        )
    response = client.post(
        f"/api/v1/claims/{claim_id}/briefs",
        headers=_headers(client, "admin"),
        json={"task": "Summarize evidence", "idempotency_key": "phase5-cross-tenant"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "claim not found"
