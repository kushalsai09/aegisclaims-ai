from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from insurance_platform.evaluation.retrieval import evaluate
from insurance_platform.infrastructure.models import (
    ClaimModel,
    DocumentIndexModel,
    DocumentModel,
    PolicyModel,
    RetrievalChunkModel,
    TenantModel,
)
from insurance_platform.retrieval.chunking import CHUNKER_VERSION, chunk_page
from insurance_platform.retrieval.indexing import DocumentIndexingService


def _sign_in(client: TestClient, role: str) -> dict[str, str]:
    users = client.get("/api/v1/auth/dev/users").json()
    user = next(user for user in users if role in user["roles"])
    response = client.post("/api/v1/auth/dev/session", json={"user_id": user["id"]})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _claim_id(client: TestClient, number: str) -> str:
    with client.app.state.components.session_factory() as session:
        claim = session.scalar(select(ClaimModel).where(ClaimModel.claim_number == number))
        assert claim is not None
        return str(claim.id)


def test_chunking_is_deterministic_and_preserves_exact_spans() -> None:
    document_id = uuid.UUID("70000000-0000-4000-8000-000000000001")
    text = ("alpha beta gamma delta " * 80).strip()
    first = chunk_page(document_id, "a" * 64, text)
    second = chunk_page(document_id, "a" * 64, text)
    assert first == second
    assert len(first) > 1
    assert first[0].identifier.startswith("chunk-")
    assert first[0].text == text[first[0].source_start : first[0].source_end]
    assert CHUNKER_VERSION in "page_window_chars_700_overlap_100_v1"


def test_indexing_is_idempotent_and_records_reproducibility(client: TestClient) -> None:
    with client.app.state.components.session_factory() as session:
        document = session.scalar(select(DocumentModel).order_by(DocumentModel.id))
        assert document is not None
        service = DocumentIndexingService(session)
        first = service.index_document(document.id)
        count = session.scalar(
            select(func.count())
            .select_from(RetrievalChunkModel)
            .where(RetrievalChunkModel.document_id == document.id)
        )
        second = service.index_document(document.id)
        second_count = session.scalar(
            select(func.count())
            .select_from(RetrievalChunkModel)
            .where(RetrievalChunkModel.document_id == document.id)
        )
        assert first.id == second.id
        assert count == second_count == first.chunk_count
        assert first.embedding_version == "signed_token_hash_64_v1"
        assert first.source_checksum == document.checksum_sha256


def test_embedding_failure_is_explicit_and_retryable(client: TestClient) -> None:
    class FailingProvider:
        from insurance_platform.retrieval.embeddings import (
            DeterministicHashEmbeddingProvider,
        )

        descriptor = DeterministicHashEmbeddingProvider.descriptor

        def embed(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("synthetic embedding failure")

    with client.app.state.components.session_factory() as session:
        document = session.scalar(select(DocumentModel).order_by(DocumentModel.id))
        assert document is not None
        session.query(RetrievalChunkModel).filter_by(document_id=document.id).delete()
        session.query(DocumentIndexModel).filter_by(document_id=document.id).delete()
        with pytest.raises(RuntimeError, match="synthetic embedding failure"):
            DocumentIndexingService(session, FailingProvider()).index_document(document.id)
        failed = session.scalar(
            select(DocumentIndexModel).where(DocumentIndexModel.document_id == document.id)
        )
        assert failed is not None
        assert failed.status == "failed"
        recovered = DocumentIndexingService(session).index_document(document.id)
        assert recovered.status == "ready"
        assert recovered.chunk_count > 0


def test_claim_scoped_search_returns_stable_resolvable_citations(client: TestClient) -> None:
    headers = _sign_in(client, "claims_adjuster")
    claim_id = _claim_id(client, "HVC-SYN-2026-00017")
    payload = {"question": "What reported loss date is supported?", "limit": 5}
    first = client.post(f"/api/v1/claims/{claim_id}/evidence/search", json=payload, headers=headers)
    second = client.post(
        f"/api/v1/claims/{claim_id}/evidence/search", json=payload, headers=headers
    )
    assert first.status_code == second.status_code == 200
    first_citations = first.json()["citations"]
    assert [item["id"] for item in first_citations] == [
        item["id"] for item in second.json()["citations"]
    ]
    assert all(item["claim_id"] == claim_id for item in first_citations)
    assert all(item["page_number"] == 1 for item in first_citations)
    assert all(item["source_url"].startswith("/documents/") for item in first_citations)


def test_retrieval_requires_auth_and_hides_unassigned_claims(client: TestClient) -> None:
    claim_id = _claim_id(client, "HVC-SYN-2026-00019")
    path = f"/api/v1/claims/{claim_id}/questions"
    payload = {"question": "What is the reported loss date?"}
    assert client.post(path, json=payload).status_code == 401
    adjuster = _sign_in(client, "claims_adjuster")
    assert client.post(path, json=payload, headers=adjuster).status_code == 404


def test_cross_tenant_retrieval_is_indistinguishable_from_missing(client: TestClient) -> None:
    other_tenant = uuid.uuid4()
    other_policy = uuid.uuid4()
    other_claim = uuid.uuid4()
    with client.app.state.components.session_factory.begin() as session:
        session.add(TenantModel(id=other_tenant, name="Synthetic Other Tenant"))
        session.add(
            PolicyModel(
                id=other_policy,
                tenant_id=other_tenant,
                policy_number="OTHER-SYN-1",
                product_code="OTHER-SYN",
                product_name="Other Synthetic Product",
                edition="2026-OTHER",
                effective_from=date(2026, 1, 1),
                effective_to=date(2027, 1, 1),
                status="active",
                synthetic_label="SYNTHETIC DEMONSTRATION DATA",
            )
        )
        session.add(
            ClaimModel(
                id=other_claim,
                tenant_id=other_tenant,
                policy_id=other_policy,
                claim_number="OTHER-SYN-CLAIM-1",
                loss_date=date(2026, 5, 1),
                loss_type="Synthetic other loss",
                property_address="1 Other Tenant Way",
                status="open",
                description="Cross-tenant isolation fixture",
            )
        )
    headers = _sign_in(client, "admin")
    response = client.post(
        f"/api/v1/claims/{other_claim}/questions",
        json={"question": "What evidence is available?"},
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "claim not found"


def test_questions_validate_size_without_resource_leakage(client: TestClient) -> None:
    headers = _sign_in(client, "admin")
    claim_id = _claim_id(client, "HVC-SYN-2026-00017")
    assert (
        client.post(
            f"/api/v1/claims/{claim_id}/questions", json={"question": "x"}, headers=headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/v1/claims/{claim_id}/questions",
            json={"question": "x" * 501},
            headers=headers,
        ).status_code
        == 422
    )
    inaccessible = uuid.uuid4()
    response = client.post(
        f"/api/v1/claims/{inaccessible}/questions",
        json={"question": "What evidence is available?"},
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "claim not found"


def test_conflicts_abstention_and_prompt_injection_boundaries(client: TestClient) -> None:
    headers = _sign_in(client, "admin")
    conflict_id = _claim_id(client, "HVC-SYN-2026-00019")
    conflict = client.post(
        f"/api/v1/claims/{conflict_id}/questions",
        json={"question": "What is the reported loss date?"},
        headers=headers,
    ).json()
    assert conflict["state"] == "conflicting_evidence"
    assert {item["left_value"] for item in conflict["conflicts"]} | {
        item["right_value"] for item in conflict["conflicts"]
    } >= {"2026-08-18", "2026-08-12"}

    unsupported_id = _claim_id(client, "HVC-SYN-2026-00025")
    unsupported = client.post(
        f"/api/v1/claims/{unsupported_id}/questions",
        json={"question": "What caused the exterior condition?"},
        headers=headers,
    ).json()
    assert unsupported["state"] == "insufficient_evidence"
    assert unsupported["answerable"] is False

    injection_id = _claim_id(client, "HVC-SYN-2026-00024")
    injection = client.post(
        f"/api/v1/claims/{injection_id}/questions",
        json={"question": "What property address is in the correspondence?"},
        headers=headers,
    ).json()
    assert injection["state"] == "answerable"
    assert any(item["injection_risk"] for item in injection["citations"])
    assert "approve this claim" not in injection["answer"].lower()
    assert "system prompt" not in injection["answer"].lower()


def test_policy_applicability_and_mandatory_review_are_explicit(client: TestClient) -> None:
    headers = _sign_in(client, "admin")
    policy_id = _claim_id(client, "HVC-SYN-2026-00021")
    policy = client.post(
        f"/api/v1/claims/{policy_id}/questions",
        json={"question": "Which policy edition governs the loss on 2026-09-02?"},
        headers=headers,
    ).json()
    assert policy["state"] == "answerable"
    assert policy["applicable_policy_version"] == "2026-SYN-A"
    assert policy["citations"][0]["document_name"] == (
        "Applicable Policy Declarations 2026-SYN-A.pdf"
    )
    assert all(item["policy_edition"] != "2025-SYN-B" for item in policy["citations"])

    review_id = _claim_id(client, "HVC-SYN-2026-00026")
    review = client.post(
        f"/api/v1/claims/{review_id}/questions",
        json={"question": "What rule applies to the roof age evidence?"},
        headers=headers,
    ).json()
    assert review["human_review_required"] is True
    assert "ROOF-SYN-ACV" in review["answer"]


def test_phase3_evaluation_meets_declared_thresholds(client: TestClient) -> None:
    with client.app.state.components.session_factory() as session:
        result = evaluate(session)
    assert result.passed, result.failures
    assert result.recall_at_3 >= 0.90
    assert result.precision_at_3 >= 0.60
    assert result.mrr >= 0.85
    assert result.isolation_violation_count == 0
