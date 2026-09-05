from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_platform.config import get_settings
from insurance_platform.delivery.components import build_components
from insurance_platform.documents.facts import extract_structured_facts
from insurance_platform.infrastructure.models import (
    AuditEventModel,
    ClaimAssignmentModel,
    ClaimModel,
    DocumentFactModel,
    DocumentModel,
    DocumentPageModel,
    DocumentProcessingEventModel,
    HumanReviewTaskModel,
    PolicyModel,
    RoleModel,
    TenantModel,
    UserModel,
    WorkflowRunModel,
)
from insurance_platform.infrastructure.repositories import DocumentRepository
from insurance_platform.ports.object_storage import ObjectStorage
from insurance_platform.retrieval.indexing import DocumentIndexingService
from insurance_platform.security.sessions import hash_password
from insurance_platform.synthetic.generator import (
    DocumentFixture,
    ScenarioFixture,
    load_manifest,
    render_text_pdf,
)

SYNTHETIC_LABEL = "SYNTHETIC DEMONSTRATION DATA"
SYNTHETIC_RULE_LABEL = "SYNTHETIC DEMONSTRATION RULE"
DEVELOPMENT_PASSWORD = "HarborView!Local2026"
TENANT_ID = uuid.UUID("10000000-0000-4000-8000-000000000001")
POLICY_ID = uuid.UUID("20000000-0000-4000-8000-000000000001")
CLAIM_ID = uuid.UUID("30000000-0000-4000-8000-000000000001")
WORKFLOW_ID = uuid.UUID("40000000-0000-4000-8000-000000000001")
NAMESPACE = uuid.UUID("87ef5a54-b199-45ee-a6c5-b455916c09c8")

ROLE_IDS = {
    "claims_adjuster": uuid.UUID("50000000-0000-4000-8000-000000000001"),
    "supervisor": uuid.UUID("50000000-0000-4000-8000-000000000002"),
    "compliance_reviewer": uuid.UUID("50000000-0000-4000-8000-000000000003"),
    "admin": uuid.UUID("50000000-0000-4000-8000-000000000004"),
}

USER_IDS = {
    "claims_adjuster": uuid.UUID("60000000-0000-4000-8000-000000000001"),
    "supervisor": uuid.UUID("60000000-0000-4000-8000-000000000002"),
    "compliance_reviewer": uuid.UUID("60000000-0000-4000-8000-000000000003"),
    "admin": uuid.UUID("60000000-0000-4000-8000-000000000004"),
}


def _stable_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{kind}:{key}")


def _claim_id(scenario: ScenarioFixture) -> uuid.UUID:
    return (
        CLAIM_ID
        if scenario.key == "straightforward_supported"
        else _stable_id("claim", scenario.key)
    )


def _document_id(scenario: ScenarioFixture, document: DocumentFixture) -> uuid.UUID:
    if scenario.key == "straightforward_supported":
        index = next(
            i for i, item in enumerate(scenario.documents, start=1) if item.name == document.name
        )
        return uuid.UUID(f"70000000-0000-4000-8000-{index:012d}")
    return _stable_id("document", f"{scenario.key}:{document.name}")


def seed(factory: sessionmaker[Session]) -> None:
    manifest = load_manifest()
    with factory.begin() as session:
        tenant = session.get(TenantModel, TENANT_ID)
        if tenant is None:
            session.add(
                TenantModel(id=TENANT_ID, name="HarborView Mutual Demonstration Organization")
            )
        session.flush()

        roles = _seed_roles(session)
        users = _seed_users(session, roles)
        if session.get(PolicyModel, POLICY_ID) is None:
            session.add(
                PolicyModel(
                    id=POLICY_ID,
                    tenant_id=TENANT_ID,
                    policy_number=manifest.policy.identifier,
                    product_code=manifest.policy.product_code,
                    product_name="HarborView HomeSecure",
                    edition=manifest.policy.edition,
                    effective_from=date.fromisoformat(manifest.policy.effective_from),
                    effective_to=date.fromisoformat(manifest.policy.effective_to),
                    status="active",
                    synthetic_label=SYNTHETIC_LABEL,
                )
            )
        session.flush()

        for scenario in manifest.scenarios:
            _seed_scenario(session, scenario, users)
        session.flush()
        repository = DocumentRepository(session)
        indexing = DocumentIndexingService(session)
        for scenario in manifest.scenarios:
            repository.rebuild_conflicts(_claim_id(scenario), TENANT_ID)
            indexing.index_claim(_claim_id(scenario), TENANT_ID)

        if (
            session.scalar(
                select(AuditEventModel).where(AuditEventModel.action == "synthetic.phase3.seeded")
            )
            is None
        ):
            session.add(
                AuditEventModel(
                    tenant_id=TENANT_ID,
                    actor_user_id=users["admin"].id,
                    action="synthetic.phase3.seeded",
                    resource_type="dataset",
                    resource_id=manifest.dataset_version,
                    outcome="success",
                    correlation_id="synthetic-phase3-seed",
                    details={
                        "label": SYNTHETIC_LABEL,
                        "rule_label": SYNTHETIC_RULE_LABEL,
                        "scenario_count": len(manifest.scenarios),
                    },
                )
            )


def _seed_roles(session: Session) -> dict[str, RoleModel]:
    descriptions = {
        "claims_adjuster": "Reviews assigned synthetic property claims",
        "supervisor": "Reviews escalated synthetic decision-support work",
        "compliance_reviewer": "Views authorized operations and compliance summaries",
        "admin": "Administers this local demonstration environment",
    }
    roles: dict[str, RoleModel] = {}
    for name, description in descriptions.items():
        role = session.get(RoleModel, ROLE_IDS[name])
        if role is None:
            role = RoleModel(id=ROLE_IDS[name], name=name, description=description)
            session.add(role)
        roles[name] = role
    return roles


def _seed_users(session: Session, roles: dict[str, RoleModel]) -> dict[str, UserModel]:
    details = {
        "claims_adjuster": ("Avery", "Morgan", "avery.morgan@example.invalid"),
        "supervisor": ("Jordan", "Lee", "jordan.lee@example.invalid"),
        "compliance_reviewer": ("Riley", "Chen", "riley.chen@example.invalid"),
        "admin": ("Casey", "Patel", "casey.patel@example.invalid"),
    }
    users: dict[str, UserModel] = {}
    for role_name, (first_name, last_name, email) in details.items():
        user = session.get(UserModel, USER_IDS[role_name])
        if user is None:
            user = UserModel(
                id=USER_IDS[role_name],
                tenant_id=TENANT_ID,
                subject=f"synthetic-{role_name}",
                first_name=first_name,
                last_name=last_name,
                display_name=f"{first_name} {last_name}",
                email=email,
                password_hash=hash_password(DEVELOPMENT_PASSWORD),
                account_status="active",
                roles=[roles[role_name]],
            )
            session.add(user)
        else:
            user.first_name = first_name
            user.last_name = last_name
            user.display_name = f"{first_name} {last_name}"
            user.email = email
            user.account_status = "active" if user.is_active else "disabled"
            if not user.password_hash:
                user.password_hash = hash_password(DEVELOPMENT_PASSWORD)
        users[role_name] = user
    return users


def _seed_scenario(
    session: Session, scenario: ScenarioFixture, users: dict[str, UserModel]
) -> None:
    claim_id = _claim_id(scenario)
    if session.get(ClaimModel, claim_id) is None:
        session.add(
            ClaimModel(
                id=claim_id,
                tenant_id=TENANT_ID,
                policy_id=POLICY_ID,
                claim_number=scenario.claim_number,
                loss_date=date.fromisoformat(scenario.loss_date),
                loss_type=scenario.loss_type,
                property_address=scenario.property_address,
                status="open",
                description=scenario.description,
            )
        )
    session.flush()
    assigned_users = (
        users.values()
        if scenario.key == "straightforward_supported"
        else (users["supervisor"], users["compliance_reviewer"], users["admin"])
    )
    for user in assigned_users:
        assignment_id = _stable_id("assignment", f"{scenario.key}:{user.id}")
        existing_assignment = session.scalar(
            select(ClaimAssignmentModel).where(
                ClaimAssignmentModel.claim_id == claim_id,
                ClaimAssignmentModel.user_id == user.id,
            )
        )
        if existing_assignment is None:
            session.add(
                ClaimAssignmentModel(
                    id=assignment_id,
                    tenant_id=TENANT_ID,
                    claim_id=claim_id,
                    user_id=user.id,
                    assignment_type="synthetic_demo_access",
                )
            )
    workflow_id = (
        WORKFLOW_ID
        if scenario.key == "straightforward_supported"
        else _stable_id("workflow", scenario.key)
    )
    workflow = session.get(WorkflowRunModel, workflow_id)
    if workflow is None:
        workflow_status = (
            "not_started" if scenario.key == "straightforward_supported" else "documents_ready"
        )
        workflow_version = (
            "phase-2-no-ai-workflow"
            if scenario.key == "straightforward_supported"
            else "phase-2-deterministic-v1"
        )
        session.add(
            WorkflowRunModel(
                id=workflow_id,
                tenant_id=TENANT_ID,
                claim_id=claim_id,
                workflow_type="document_ingestion",
                status=workflow_status,
                version=workflow_version,
                correlation_id="synthetic-phase2-seed",
            )
        )
    elif scenario.key == "straightforward_supported":
        workflow.workflow_type = "claims_intelligence"
        workflow.status = "not_started"
        workflow.version = "phase-2-no-ai-workflow"
    for document in scenario.documents:
        _seed_document(session, scenario, document, users["admin"])
    if scenario.mandatory_human_review:
        review_id = _stable_id("review", scenario.key)
        if session.get(HumanReviewTaskModel, review_id) is None:
            session.add(
                HumanReviewTaskModel(
                    id=review_id,
                    tenant_id=TENANT_ID,
                    claim_id=claim_id,
                    workflow_run_id=workflow_id,
                    assigned_to_user_id=users["supervisor"].id,
                    status="open",
                    reason_code="synthetic_mandatory_review",
                    reason=("SYNTHETIC DEMONSTRATION RULE — this scenario requires human review."),
                    version=1,
                )
            )


def _seed_document(
    session: Session,
    scenario: ScenarioFixture,
    fixture: DocumentFixture,
    uploader: UserModel,
) -> None:
    document_id = _document_id(scenario, fixture)
    content = render_text_pdf(fixture)
    checksum = hashlib.sha256(content).hexdigest()
    claim_id = _claim_id(scenario)
    base_key = f"{TENANT_ID}/{claim_id}/{document_id}"
    document = session.get(DocumentModel, document_id)
    if document is None:
        document = DocumentModel(
            id=document_id,
            tenant_id=TENANT_ID,
            claim_id=claim_id,
            name=fixture.name,
            original_filename=fixture.name,
            document_type=fixture.expected_type,
            storage_key=f"{base_key}/original/{checksum}.pdf",
            normalized_storage_key=f"{base_key}/derived/normalized.txt",
            extraction_artifact_key=f"{base_key}/derived/extraction.json",
            content_type="application/pdf",
            detected_mime_type="application/pdf",
            checksum_sha256=checksum,
            size_bytes=len(content),
            processing_status="ready",
            extraction_status="extracted",
            page_count=len(fixture.pages),
            classification_method="synthetic_manifest_assignment",
            classification_version="phase2-synthetic-v1",
            classification_signals={"expected_type": [fixture.expected_type]},
            injection_risk=fixture.injection_risk,
            uploaded_by_user_id=uploader.id,
            synthetic_label=SYNTHETIC_LABEL,
            updated_at=datetime.now(UTC),
        )
        session.add(document)
    else:
        document.original_filename = fixture.name
        document.document_type = fixture.expected_type
        document.storage_key = f"{base_key}/original/{checksum}.pdf"
        document.normalized_storage_key = f"{base_key}/derived/normalized.txt"
        document.extraction_artifact_key = f"{base_key}/derived/extraction.json"
        document.content_type = "application/pdf"
        document.detected_mime_type = "application/pdf"
        document.checksum_sha256 = checksum
        document.size_bytes = len(content)
        document.processing_status = "ready"
        document.extraction_status = "extracted"
        document.page_count = len(fixture.pages)
        document.classification_method = "synthetic_manifest_assignment"
        document.classification_version = "phase2-synthetic-v1"
        document.classification_signals = {"expected_type": [fixture.expected_type]}
        document.injection_risk = fixture.injection_risk
        document.uploaded_by_user_id = uploader.id
        document.updated_at = datetime.now(UTC)
    session.flush()
    if not document.pages:
        for page_number, text in enumerate(fixture.pages, start=1):
            session.add(
                DocumentPageModel(
                    tenant_id=TENANT_ID,
                    document_id=document_id,
                    page_number=page_number,
                    text=text,
                    text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                    extraction_method=fixture.extraction_method,
                    extraction_version="phase2-synthetic-v1",
                )
            )
        for fact in extract_structured_facts(fixture.pages):
            session.add(
                DocumentFactModel(
                    tenant_id=TENANT_ID,
                    claim_id=claim_id,
                    document_id=document_id,
                    page_number=fact.page_number,
                    fact_type=fact.fact_type,
                    raw_source_span=fact.raw_source_span,
                    normalized_value=fact.normalized_value,
                    extraction_method="deterministic_regex",
                    extraction_version="1",
                )
            )
    if not document.processing_events:
        for status, detail in [
            ("uploaded", "Synthetic fixture accepted"),
            ("validating", "Synthetic fixture integrity verified"),
            ("stored", "Immutable original generated"),
            ("extracting", "Page text fixture preserved"),
            ("classifying", "Manifest category assigned"),
            ("normalizing", "Structured facts generated"),
            ("ready", "Synthetic fixture processing completed"),
        ]:
            session.add(
                DocumentProcessingEventModel(
                    tenant_id=TENANT_ID,
                    document_id=document_id,
                    status=status,
                    detail=detail,
                    correlation_id="synthetic-phase2-seed",
                )
            )


async def store_seed_documents(storage: ObjectStorage) -> None:
    manifest = load_manifest()
    await storage.ensure_ready()
    for scenario in manifest.scenarios:
        claim_id = _claim_id(scenario)
        for fixture in scenario.documents:
            document_id = _document_id(scenario, fixture)
            content = render_text_pdf(fixture)
            checksum = hashlib.sha256(content).hexdigest()
            base_key = f"{TENANT_ID}/{claim_id}/{document_id}"
            await storage.put_bytes(
                f"{base_key}/original/{checksum}.pdf", content, "application/pdf"
            )
            normalized = "\n\n".join(
                f"--- Page {number} ---\n{text}"
                for number, text in enumerate(fixture.pages, start=1)
            ).encode()
            await storage.put_bytes(f"{base_key}/derived/normalized.txt", normalized, "text/plain")


def main() -> None:
    settings = get_settings()
    components = build_components(settings)
    seed(components.session_factory)
    asyncio.run(store_seed_documents(components.object_storage))
    components.engine.dispose()


if __name__ == "__main__":
    main()
