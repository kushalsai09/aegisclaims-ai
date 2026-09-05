from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from insurance_platform.application.schemas import (
    ClaimSummaryView,
    ClaimView,
    ClaimWorkspaceView,
    DashboardView,
    DocumentDetailView,
    DocumentFactView,
    DocumentPageView,
    DocumentView,
    FactConflictView,
    FutureSectionView,
    OperationsSummaryView,
    PolicyView,
    ProcessingEventView,
    ReviewTaskView,
    UserView,
    WorkflowView,
)
from insurance_platform.domain.entities import Actor
from insurance_platform.domain.enums import RoleName
from insurance_platform.infrastructure.models import (
    ClaimAssignmentModel,
    ClaimModel,
    DocumentModel,
    FactConflictModel,
    ReviewArtifactModel,
    UserModel,
    WorkflowRunModel,
)
from insurance_platform.infrastructure.repositories import (
    ClaimRepository,
    DocumentRepository,
    OperationsRepository,
    ReviewRepository,
    UserRepository,
)

SYNTHETIC_NOTICE = (
    "SYNTHETIC DEMONSTRATION DATA — fictional portfolio content; not a real insurer record."
)

FUTURE_SECTIONS = [
    FutureSectionView(
        key="support_assessment",
        title="Support Assessment",
        description=(
            "No claim recommendation, confidence score, or automated decision is generated."
        ),
    ),
    FutureSectionView(
        key="human_review",
        title="Autonomous Claim Decisions",
        description=(
            "Not implemented by design. Evidence assistance cannot approve, "
            "deny, pay, contact, or close a claim."
        ),
    ),
]


class PlatformService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._claims = ClaimRepository(session)
        self._documents = DocumentRepository(session)
        self._reviews = ReviewRepository(session)
        self._operations = OperationsRepository(session)

    def list_dev_users(self) -> list[UserView]:
        return [
            UserView(
                id=user.id,
                display_name=user.display_name,
                email=user.email,
                roles=sorted(role.name for role in user.roles),
            )
            for user in self._users.list_active()
        ]

    def dashboard(self, actor: Actor) -> DashboardView:
        can_review = bool(actor.roles & {RoleName.SUPERVISOR, RoleName.ADMIN})
        return DashboardView(
            assigned_claims=self._claims.count_for_actor(actor),
            open_reviews=self._reviews.count_open(actor) if can_review else 0,
        )

    def list_claims(
        self, actor: Actor, *, limit: int = 100, offset: int = 0
    ) -> list[ClaimSummaryView]:
        claims = self._claims.list_for_actor(actor, limit=limit, offset=offset)
        claim_ids = [claim.id for claim in claims]
        latest_workflows: dict[UUID, WorkflowRunModel] = {}
        assignees: dict[UUID, str] = {}
        if claim_ids:
            workflows = self._session.scalars(
                select(WorkflowRunModel)
                .where(
                    WorkflowRunModel.tenant_id == actor.tenant_id,
                    WorkflowRunModel.claim_id.in_(claim_ids),
                )
                .order_by(WorkflowRunModel.created_at.desc())
            )
            for workflow in workflows:
                latest_workflows.setdefault(workflow.claim_id, workflow)
            assignment_rows = self._session.execute(
                select(ClaimAssignmentModel.claim_id, UserModel.display_name)
                .join(UserModel, UserModel.id == ClaimAssignmentModel.user_id)
                .where(
                    ClaimAssignmentModel.tenant_id == actor.tenant_id,
                    ClaimAssignmentModel.claim_id.in_(claim_ids),
                    ClaimAssignmentModel.assignment_type.in_(["assigned", "synthetic_demo_access"]),
                )
                .order_by(UserModel.display_name)
            )
            for claim_id, display_name in assignment_rows:
                assignees.setdefault(claim_id, display_name)
        result: list[ClaimSummaryView] = []
        for claim in claims:
            latest_workflow = latest_workflows.get(claim.id)
            result.append(
                ClaimSummaryView(
                    id=claim.id,
                    claim_number=claim.claim_number,
                    loss_date=claim.loss_date,
                    loss_type=claim.loss_type,
                    property_address=claim.property_address,
                    status=claim.status,
                    policy_number=claim.policy.policy_number,
                    workflow_status=(latest_workflow.status if latest_workflow else "not_started"),
                    assigned_to=assignees.get(claim.id),
                    updated_at=claim.updated_at,
                )
            )
        return result

    def _assigned_to(self, claim_id: UUID) -> str | None:
        return self._session.scalar(
            select(UserModel.display_name)
            .join(ClaimAssignmentModel, ClaimAssignmentModel.user_id == UserModel.id)
            .where(
                ClaimAssignmentModel.claim_id == claim_id,
                ClaimAssignmentModel.assignment_type.in_(["assigned", "synthetic_demo_access"]),
            )
            .order_by(UserModel.display_name)
            .limit(1)
        )

    def claim_workspace(self, claim_id: UUID, actor: Actor) -> ClaimWorkspaceView | None:
        claim = self._claims.get_for_actor(claim_id, actor)
        if claim is None:
            return None
        workflow = self._claims.latest_workflow(claim_id, actor)
        return ClaimWorkspaceView(
            claim=ClaimView.model_validate(claim),
            policy=PolicyView.model_validate(claim.policy),
            documents=[
                self._document_view(document)
                for document in self._claims.documents(claim_id, actor)
            ],
            conflicts=[
                self._conflict_view(conflict)
                for conflict in self._documents.conflicts(claim_id, actor.tenant_id)
            ],
            workflow=WorkflowView.model_validate(workflow) if workflow else None,
            human_review_status=self._claims.review_status(claim_id, actor),
            future_sections=FUTURE_SECTIONS,
            synthetic_notice=SYNTHETIC_NOTICE,
        )

    def document_detail(self, document_id: UUID, actor: Actor) -> DocumentDetailView | None:
        document = self._documents.get_for_actor(document_id, actor)
        if document is None:
            return None
        conflicts = [
            conflict
            for conflict in self._documents.conflicts(document.claim_id, actor.tenant_id)
            if conflict.left_fact.document_id == document.id
            or conflict.right_fact.document_id == document.id
        ]
        return DocumentDetailView(
            document=self._document_view(document),
            pages=[
                DocumentPageView.model_validate(page)
                for page in sorted(document.pages, key=lambda page: page.page_number)
            ],
            facts=[
                DocumentFactView.model_validate(fact)
                for fact in sorted(
                    document.facts, key=lambda fact: (fact.page_number, fact.fact_type)
                )
            ],
            conflicts=[self._conflict_view(conflict) for conflict in conflicts],
            processing_history=[
                ProcessingEventView.model_validate(event)
                for event in sorted(document.processing_events, key=lambda event: event.created_at)
            ],
            error_code=document.error_code,
            error_detail=document.error_detail,
        )

    @staticmethod
    def _document_view(document: DocumentModel) -> DocumentView:
        return DocumentView(
            id=document.id,
            name=document.name,
            document_type=document.document_type,
            content_type=document.content_type,
            detected_mime_type=document.detected_mime_type,
            processing_status=document.processing_status,
            extraction_status=document.extraction_status,
            page_count=document.page_count,
            size_bytes=document.size_bytes,
            checksum_sha256=document.checksum_sha256 or "",
            uploaded_by=document.uploaded_by.display_name if document.uploaded_by else None,
            uploaded_at=document.created_at,
            injection_risk=document.injection_risk,
            synthetic_label=document.synthetic_label,
            created_at=document.created_at,
        )

    @staticmethod
    def _conflict_view(conflict: FactConflictModel) -> FactConflictView:
        return FactConflictView(
            id=conflict.id,
            fact_type=conflict.fact_type,
            status=conflict.status,
            detection_method=conflict.detection_method,
            left_document_name=conflict.left_fact.document.name,
            right_document_name=conflict.right_fact.document.name,
            left=DocumentFactView.model_validate(conflict.left_fact),
            right=DocumentFactView.model_validate(conflict.right_fact),
        )

    def review_queue(
        self, actor: Actor, *, limit: int = 100, offset: int = 0
    ) -> list[ReviewTaskView]:
        tasks = self._reviews.list_open(actor, limit=limit, offset=offset)
        workflow_ids = [task.workflow_run_id for task in tasks if task.workflow_run_id]
        claim_ids = {task.claim_id for task in tasks}
        user_ids = {task.assigned_to_user_id for task in tasks if task.assigned_to_user_id}
        workflows = {
            item.id: item
            for item in self._session.scalars(
                select(WorkflowRunModel).where(
                    WorkflowRunModel.tenant_id == actor.tenant_id,
                    WorkflowRunModel.id.in_(workflow_ids),
                )
            )
        }
        artifacts = {
            item.workflow_run_id: item
            for item in self._session.scalars(
                select(ReviewArtifactModel).where(
                    ReviewArtifactModel.tenant_id == actor.tenant_id,
                    ReviewArtifactModel.workflow_run_id.in_(workflow_ids),
                )
            )
        }
        claims = {
            item.id: item
            for item in self._session.scalars(
                select(ClaimModel).where(
                    ClaimModel.tenant_id == actor.tenant_id,
                    ClaimModel.id.in_(claim_ids),
                )
            )
        }
        users = {
            item.id: item
            for item in self._session.scalars(
                select(UserModel).where(
                    UserModel.tenant_id == actor.tenant_id,
                    UserModel.id.in_(user_ids),
                )
            )
        }
        result: list[ReviewTaskView] = []
        for task in tasks:
            workflow = workflows.get(task.workflow_run_id) if task.workflow_run_id else None
            if workflow and workflow.correlation_id.startswith("phase4-evaluation-"):
                continue
            artifact = artifacts.get(task.workflow_run_id) if task.workflow_run_id else None
            content = artifact.content if artifact else {}
            flags: list[str] = []
            if content.get("conflicting_evidence"):
                flags.append("conflict")
            if content.get("ambiguous_evidence"):
                flags.append("ambiguity")
            if content.get("missing_information"):
                flags.append("missing_information")
            if content.get("untrusted_content_flags"):
                flags.append("untrusted_content")
            claim = claims.get(task.claim_id)
            assigned_user = (
                users.get(task.assigned_to_user_id) if task.assigned_to_user_id else None
            )
            result.append(
                ReviewTaskView(
                    id=task.id,
                    claim_id=task.claim_id,
                    status=task.status,
                    reason_code=task.reason_code,
                    reason=task.reason,
                    created_at=task.created_at,
                    workflow_id=task.workflow_run_id,
                    workflow_status=workflow.status if workflow else None,
                    safety_flags=flags,
                    claim_number=claim.claim_number if claim else None,
                    assigned_to=assigned_user.display_name if assigned_user else None,
                )
            )
        return result

    def operations(self, actor: Actor) -> OperationsSummaryView:
        return OperationsSummaryView(**self._operations.counts(actor.tenant_id))
