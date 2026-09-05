from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from insurance_platform.domain.entities import Actor
from insurance_platform.domain.enums import RoleName
from insurance_platform.infrastructure.models import (
    AuditEventModel,
    ClaimAssignmentModel,
    ClaimModel,
    DocumentFactModel,
    DocumentModel,
    FactConflictModel,
    HumanReviewTaskModel,
    UserModel,
    WorkflowRunModel,
)


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_active(self) -> list[UserModel]:
        statement = (
            select(UserModel)
            .where(UserModel.is_active.is_(True))
            .options(selectinload(UserModel.roles))
            .order_by(UserModel.display_name)
        )
        return list(self._session.scalars(statement).unique())

    def get_active(self, user_id: UUID, tenant_id: UUID | None = None) -> UserModel | None:
        statement = (
            select(UserModel)
            .where(UserModel.id == user_id, UserModel.is_active.is_(True))
            .options(selectinload(UserModel.roles))
        )
        if tenant_id is not None:
            statement = statement.where(UserModel.tenant_id == tenant_id)
        return self._session.scalar(statement)

    def get(self, user_id: UUID, tenant_id: UUID) -> UserModel | None:
        return self._session.scalar(
            select(UserModel)
            .where(UserModel.id == user_id, UserModel.tenant_id == tenant_id)
            .options(selectinload(UserModel.roles))
        )

    def get_by_subject(self, subject: str, tenant_id: UUID) -> UserModel | None:
        return self._session.scalar(
            select(UserModel)
            .where(
                UserModel.subject == subject,
                UserModel.tenant_id == tenant_id,
                UserModel.is_active.is_(True),
                UserModel.account_status == "active",
            )
            .options(selectinload(UserModel.roles))
        )


class ClaimRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_actor(
        self, actor: Actor, *, limit: int = 100, offset: int = 0
    ) -> list[ClaimModel]:
        statement = (
            select(ClaimModel)
            .where(ClaimModel.tenant_id == actor.tenant_id)
            .order_by(ClaimModel.created_at.desc())
        )
        if not actor.is_admin:
            statement = statement.join(ClaimAssignmentModel).where(
                ClaimAssignmentModel.user_id == actor.user_id,
                ClaimAssignmentModel.tenant_id == actor.tenant_id,
            )
        return list(self._session.scalars(statement.limit(limit).offset(offset)).unique())

    def count_for_actor(self, actor: Actor) -> int:
        statement = (
            select(func.count())
            .select_from(ClaimModel)
            .where(ClaimModel.tenant_id == actor.tenant_id)
        )
        if not actor.is_admin:
            statement = statement.join(ClaimAssignmentModel).where(
                ClaimAssignmentModel.user_id == actor.user_id,
                ClaimAssignmentModel.tenant_id == actor.tenant_id,
            )
        return int(self._session.scalar(statement) or 0)

    def get_for_actor(self, claim_id: UUID, actor: Actor) -> ClaimModel | None:
        statement = select(ClaimModel).where(
            ClaimModel.id == claim_id, ClaimModel.tenant_id == actor.tenant_id
        )
        if not actor.is_admin:
            statement = statement.join(ClaimAssignmentModel).where(
                ClaimAssignmentModel.user_id == actor.user_id,
                ClaimAssignmentModel.tenant_id == actor.tenant_id,
            )
        return self._session.scalar(statement)

    def documents(self, claim_id: UUID, actor: Actor) -> list[DocumentModel]:
        statement = (
            select(DocumentModel)
            .where(
                DocumentModel.claim_id == claim_id,
                DocumentModel.tenant_id == actor.tenant_id,
            )
            .order_by(DocumentModel.created_at)
        )
        return list(self._session.scalars(statement))

    def latest_workflow(self, claim_id: UUID, actor: Actor) -> WorkflowRunModel | None:
        statement = (
            select(WorkflowRunModel)
            .where(
                WorkflowRunModel.claim_id == claim_id,
                WorkflowRunModel.tenant_id == actor.tenant_id,
            )
            .order_by(WorkflowRunModel.created_at.desc())
            .limit(1)
        )
        return self._session.scalar(statement)

    def review_status(self, claim_id: UUID, actor: Actor) -> str:
        active = self._session.scalar(
            select(HumanReviewTaskModel.status)
            .where(
                HumanReviewTaskModel.claim_id == claim_id,
                HumanReviewTaskModel.tenant_id == actor.tenant_id,
                HumanReviewTaskModel.status.in_(["open", "assigned"]),
            )
            .order_by(HumanReviewTaskModel.created_at.desc())
            .limit(1)
        )
        if active:
            return active
        statement = (
            select(HumanReviewTaskModel.status)
            .where(
                HumanReviewTaskModel.claim_id == claim_id,
                HumanReviewTaskModel.tenant_id == actor.tenant_id,
            )
            .order_by(HumanReviewTaskModel.created_at.desc())
            .limit(1)
        )
        return self._session.scalar(statement) or "not_required"


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def duplicate(self, tenant_id: UUID, claim_id: UUID, checksum: str) -> DocumentModel | None:
        return self._session.scalar(
            select(DocumentModel).where(
                DocumentModel.tenant_id == tenant_id,
                DocumentModel.claim_id == claim_id,
                DocumentModel.checksum_sha256 == checksum,
            )
        )

    def get_for_actor(self, document_id: UUID, actor: Actor) -> DocumentModel | None:
        statement = select(DocumentModel).where(
            DocumentModel.id == document_id, DocumentModel.tenant_id == actor.tenant_id
        )
        if not actor.is_admin:
            statement = statement.join(
                ClaimAssignmentModel,
                ClaimAssignmentModel.claim_id == DocumentModel.claim_id,
            ).where(
                ClaimAssignmentModel.user_id == actor.user_id,
                ClaimAssignmentModel.tenant_id == actor.tenant_id,
            )
        return self._session.scalar(statement)

    def conflicts(self, claim_id: UUID, tenant_id: UUID) -> list[FactConflictModel]:
        return list(
            self._session.scalars(
                select(FactConflictModel)
                .where(
                    FactConflictModel.claim_id == claim_id,
                    FactConflictModel.tenant_id == tenant_id,
                )
                .order_by(FactConflictModel.created_at)
            )
        )

    def rebuild_conflicts(self, claim_id: UUID, tenant_id: UUID) -> list[FactConflictModel]:
        self._session.execute(
            delete(FactConflictModel).where(
                FactConflictModel.claim_id == claim_id,
                FactConflictModel.tenant_id == tenant_id,
            )
        )
        comparable = {
            "reported_loss_date",
            "property_address",
            "policy_identifier",
            "policy_edition",
        }
        facts = list(
            self._session.scalars(
                select(DocumentFactModel)
                .where(
                    DocumentFactModel.claim_id == claim_id,
                    DocumentFactModel.tenant_id == tenant_id,
                    DocumentFactModel.fact_type.in_(comparable),
                )
                .order_by(DocumentFactModel.fact_type, DocumentFactModel.created_at)
            )
        )
        conflicts: list[FactConflictModel] = []
        for index, left in enumerate(facts):
            for right in facts[index + 1 :]:
                if right.fact_type != left.fact_type:
                    continue
                if right.normalized_value == left.normalized_value:
                    continue
                conflict = FactConflictModel(
                    tenant_id=tenant_id,
                    claim_id=claim_id,
                    fact_type=left.fact_type,
                    left_fact_id=left.id,
                    right_fact_id=right.id,
                    status="conflict_detected",
                    detection_method="deterministic_exact_v1",
                )
                self._session.add(conflict)
                conflicts.append(conflict)
        self._session.flush()
        return conflicts


class ReviewRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_open(
        self, actor: Actor, *, limit: int = 100, offset: int = 0
    ) -> list[HumanReviewTaskModel]:
        statement = (
            select(HumanReviewTaskModel)
            .where(
                HumanReviewTaskModel.tenant_id == actor.tenant_id,
                HumanReviewTaskModel.status.in_(["open", "assigned"]),
            )
            .order_by(HumanReviewTaskModel.created_at)
        )
        return list(self._session.scalars(statement.limit(limit).offset(offset)))

    def count_open(self, actor: Actor) -> int:
        return int(
            self._session.scalar(
                select(func.count())
                .select_from(HumanReviewTaskModel)
                .where(
                    HumanReviewTaskModel.tenant_id == actor.tenant_id,
                    HumanReviewTaskModel.status.in_(["open", "assigned"]),
                )
            )
            or 0
        )


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, event: AuditEventModel) -> None:
        self._session.add(event)
        self._session.commit()


class OperationsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def counts(self, tenant_id: UUID) -> dict[str, int]:
        return {
            "claim_count": int(
                self._session.scalar(
                    select(func.count())
                    .select_from(ClaimModel)
                    .where(ClaimModel.tenant_id == tenant_id)
                )
                or 0
            ),
            "document_count": int(
                self._session.scalar(
                    select(func.count())
                    .select_from(DocumentModel)
                    .where(DocumentModel.tenant_id == tenant_id)
                )
                or 0
            ),
            "workflow_count": int(
                self._session.scalar(
                    select(func.count())
                    .select_from(WorkflowRunModel)
                    .where(WorkflowRunModel.tenant_id == tenant_id)
                )
                or 0
            ),
            "review_count": int(
                self._session.scalar(
                    select(func.count())
                    .select_from(HumanReviewTaskModel)
                    .where(HumanReviewTaskModel.tenant_id == tenant_id)
                )
                or 0
            ),
        }


def actor_from_user(user: UserModel) -> Actor:
    roles = frozenset(RoleName(role.name) for role in user.roles)
    return Actor(
        user_id=user.id,
        tenant_id=user.tenant_id,
        subject=user.subject,
        display_name=user.display_name,
        roles=roles,
    )
