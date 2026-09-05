from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from insurance_platform.application.schemas import (
    ControlledWorkflowView,
    ReviewArtifactView,
    WorkflowEventView,
    WorkflowHistoryView,
)
from insurance_platform.domain.entities import Actor
from insurance_platform.infrastructure.models import (
    AuditEventModel,
    HumanReviewTaskModel,
    ReviewArtifactModel,
    WorkflowCheckpointModel,
    WorkflowEventModel,
    WorkflowReviewActionModel,
    WorkflowRunModel,
)
from insurance_platform.infrastructure.repositories import ClaimRepository
from insurance_platform.workflows.engine import ControlledWorkflowGraph
from insurance_platform.workflows.state import WORKFLOW_VERSION, WorkflowState


class WorkflowNotFoundError(Exception):
    pass


class WorkflowConflictError(Exception):
    pass


class WorkflowExecutionError(Exception):
    pass


class ControlledWorkflowService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._claims = ClaimRepository(session)

    def start(
        self,
        *,
        claim_id: UUID,
        actor: Actor,
        task: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> ControlledWorkflowView:
        claim = self._claims.get_for_actor(claim_id, actor)
        if claim is None:
            raise WorkflowNotFoundError("claim not found")
        existing = self._session.scalar(
            select(WorkflowRunModel).where(
                WorkflowRunModel.tenant_id == actor.tenant_id,
                WorkflowRunModel.claim_id == claim_id,
                WorkflowRunModel.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if existing.task != task:
                raise WorkflowConflictError("idempotency key was already used for another task")
            return self.view(existing)

        fingerprint = self._fingerprint(claim_id, actor, task)
        now = datetime.now(UTC)
        workflow = WorkflowRunModel(
            tenant_id=actor.tenant_id,
            claim_id=claim_id,
            workflow_type="claim_evidence_review",
            status="created",
            version=WORKFLOW_VERSION,
            correlation_id=correlation_id,
            initiating_actor_id=actor.user_id,
            task=task,
            current_stage="created",
            checkpoint_version=0,
            idempotency_key=idempotency_key,
            input_fingerprint=fingerprint,
            applicable_policy_edition=claim.policy.edition,
            human_review_required=False,
            approval_state="not_required",
            retry_count=0,
            max_retries=2,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(workflow)
        self._session.flush()
        state = self._initial_state(workflow, actor)
        self._persist(workflow, state, actor.user_id, "workflow.created", None)
        try:
            graph = ControlledWorkflowGraph(self._session, actor)
            last_stage = state["current_stage"]
            for next_state in graph.stream(state):
                if next_state["current_stage"] == last_stage:
                    continue
                previous = workflow.status
                self._persist(
                    workflow,
                    next_state,
                    None,
                    f"workflow.{next_state['current_stage']}",
                    previous,
                )
                state = next_state
                last_stage = state["current_stage"]
            self._upsert_artifact(workflow, ControlledWorkflowGraph.artifact(state))
            if state["human_review_required"]:
                self._upsert_review_task(workflow, state)
            else:
                workflow.completed_at = datetime.now(UTC)
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            persisted = self._session.get(WorkflowRunModel, workflow.id)
            if persisted is not None:
                failed = self._state_from_checkpoint(persisted)
                failed.update(
                    {
                        "current_stage": "failed",
                        "status": "failed",
                        "error_code": "workflow_node_failure",
                        "error_detail": str(exc)[:500],
                    }
                )
                self._persist(persisted, failed, None, "workflow.failed", persisted.status)
                self._session.commit()
            raise WorkflowExecutionError("workflow execution failed") from exc
        return self.view(workflow)

    def get(self, workflow_id: UUID, actor: Actor) -> WorkflowRunModel:
        workflow = self._session.scalar(
            select(WorkflowRunModel).where(
                WorkflowRunModel.id == workflow_id,
                WorkflowRunModel.tenant_id == actor.tenant_id,
            )
        )
        if workflow is None or self._claims.get_for_actor(workflow.claim_id, actor) is None:
            raise WorkflowNotFoundError("workflow not found")
        return workflow

    def latest(self, claim_id: UUID, actor: Actor) -> ControlledWorkflowView | None:
        if self._claims.get_for_actor(claim_id, actor) is None:
            raise WorkflowNotFoundError("claim not found")
        workflow = self._session.scalar(
            select(WorkflowRunModel)
            .where(
                WorkflowRunModel.claim_id == claim_id,
                WorkflowRunModel.tenant_id == actor.tenant_id,
                WorkflowRunModel.version == WORKFLOW_VERSION,
            )
            .order_by(WorkflowRunModel.created_at.desc())
            .limit(1)
        )
        return self.view(workflow) if workflow else None

    def history(self, workflow: WorkflowRunModel) -> WorkflowHistoryView:
        events = list(
            self._session.scalars(
                select(WorkflowEventModel)
                .where(WorkflowEventModel.workflow_run_id == workflow.id)
                .order_by(WorkflowEventModel.sequence)
            )
        )
        return WorkflowHistoryView(
            workflow_id=workflow.id,
            events=[WorkflowEventView.model_validate(event) for event in events],
        )

    def review(
        self,
        *,
        workflow: WorkflowRunModel,
        actor: Actor,
        action: str,
        reason: str,
        expected_version: int,
        idempotency_key: str,
    ) -> ControlledWorkflowView:
        duplicate = self._session.scalar(
            select(WorkflowReviewActionModel).where(
                WorkflowReviewActionModel.workflow_run_id == workflow.id,
                WorkflowReviewActionModel.idempotency_key == idempotency_key,
            )
        )
        if duplicate is not None:
            if duplicate.action != action or duplicate.reason != reason:
                raise WorkflowConflictError("idempotency key was already used for another action")
            return self.view(workflow)
        if workflow.status != "awaiting_human_review":
            raise WorkflowConflictError("workflow is not awaiting human review")
        if workflow.checkpoint_version != expected_version:
            raise WorkflowConflictError("stale checkpoint version; reload before reviewing")
        current_fingerprint = self._fingerprint(workflow.claim_id, actor, workflow.task or "")
        if current_fingerprint != workflow.input_fingerprint:
            raise WorkflowConflictError(
                "claim evidence changed after this workflow checkpoint; start a new workflow"
            )

        terminal = action in {"acknowledge", "approve_proposed_next_step", "reject_proposal"}
        new_status = "completed" if terminal else "awaiting_additional_information"
        approval = {
            "acknowledge": "acknowledged",
            "approve_proposed_next_step": "proposal_approved",
            "reject_proposal": "proposal_rejected",
            "request_more_information": "more_information_requested",
            "return_for_evidence_review": "returned_for_evidence_review",
        }[action]
        updated = self._session.execute(
            update(WorkflowRunModel)
            .where(
                WorkflowRunModel.id == workflow.id,
                WorkflowRunModel.checkpoint_version == expected_version,
                WorkflowRunModel.status == "awaiting_human_review",
            )
            .values(
                status=new_status,
                current_stage=new_status,
                approval_state=approval,
                checkpoint_version=WorkflowRunModel.checkpoint_version + 1,
                completed_at=datetime.now(UTC) if terminal else None,
                updated_at=datetime.now(UTC),
            )
        )
        if getattr(updated, "rowcount", 0) != 1:
            self._session.rollback()
            raise WorkflowConflictError("workflow changed while the review was submitted")
        self._session.add(
            WorkflowReviewActionModel(
                workflow_run_id=workflow.id,
                tenant_id=workflow.tenant_id,
                actor_user_id=actor.user_id,
                action=action,
                reason=reason,
                expected_checkpoint_version=expected_version,
                idempotency_key=idempotency_key,
            )
        )
        task = self._session.scalar(
            select(HumanReviewTaskModel).where(HumanReviewTaskModel.workflow_run_id == workflow.id)
        )
        if task is not None:
            task.status = "completed" if terminal else "open"
            task.assigned_to_user_id = actor.user_id
            task.version += 1
            task.updated_at = datetime.now(UTC)
            task.completed_at = datetime.now(UTC) if terminal else None
        self._session.expire(workflow)
        self._session.refresh(workflow)
        state = self._state_from_checkpoint(workflow)
        state.update(
            {
                "status": new_status,
                "current_stage": new_status,
                "approval_state": approval,
                "checkpoint_version": workflow.checkpoint_version,
            }
        )
        self._checkpoint_and_event(
            workflow,
            state,
            actor.user_id,
            f"review.{action}",
            "awaiting_human_review",
            {"reason": reason},
        )
        self._audit(workflow, actor.user_id, f"workflow.review.{action}", "success")
        self._session.commit()
        return self.view(workflow)

    def cancel(self, workflow: WorkflowRunModel, actor: Actor) -> ControlledWorkflowView:
        if workflow.status in {"completed", "cancelled"}:
            raise WorkflowConflictError("completed or cancelled workflow cannot be cancelled")
        previous = workflow.status
        state = self._state_from_checkpoint(workflow)
        state.update(
            {"status": "cancelled", "current_stage": "cancelled", "approval_state": "cancelled"}
        )
        self._persist(workflow, state, actor.user_id, "workflow.cancelled", previous)
        workflow.completed_at = datetime.now(UTC)
        task = self._session.scalar(
            select(HumanReviewTaskModel).where(HumanReviewTaskModel.workflow_run_id == workflow.id)
        )
        if task:
            task.status = "cancelled"
            task.completed_at = datetime.now(UTC)
        self._session.commit()
        return self.view(workflow)

    def retry(
        self,
        workflow: WorkflowRunModel,
        actor: Actor,
        idempotency_key: str,
    ) -> ControlledWorkflowView:
        duplicate = self._session.scalar(
            select(WorkflowReviewActionModel).where(
                WorkflowReviewActionModel.workflow_run_id == workflow.id,
                WorkflowReviewActionModel.idempotency_key == idempotency_key,
            )
        )
        if duplicate is not None:
            return self.view(workflow)
        if workflow.status not in {"failed", "awaiting_additional_information"}:
            raise WorkflowConflictError("only failed or information-blocked workflows can retry")
        if workflow.retry_count >= workflow.max_retries:
            raise WorkflowConflictError("workflow retry limit has been reached")
        self._session.add(
            WorkflowReviewActionModel(
                workflow_run_id=workflow.id,
                tenant_id=workflow.tenant_id,
                actor_user_id=actor.user_id,
                action="retry",
                reason="Bounded workflow retry requested.",
                expected_checkpoint_version=workflow.checkpoint_version,
                idempotency_key=idempotency_key,
            )
        )
        workflow.retry_count += 1
        workflow.error_code = None
        workflow.error_detail = None
        workflow.input_fingerprint = self._fingerprint(
            workflow.claim_id, actor, workflow.task or ""
        )
        state = self._initial_state(workflow, actor)
        state["retry_count"] = workflow.retry_count
        graph = ControlledWorkflowGraph(self._session, actor)
        last_stage = ""
        for next_state in graph.stream(state):
            if next_state["current_stage"] == last_stage:
                continue
            previous = workflow.status
            self._persist(
                workflow,
                next_state,
                actor.user_id,
                f"workflow.retry.{next_state['current_stage']}",
                previous,
            )
            state = next_state
            last_stage = state["current_stage"]
        self._upsert_artifact(workflow, ControlledWorkflowGraph.artifact(state))
        if state["human_review_required"]:
            self._upsert_review_task(workflow, state)
        else:
            workflow.completed_at = datetime.now(UTC)
        self._session.commit()
        return self.view(workflow)

    def view(self, workflow: WorkflowRunModel) -> ControlledWorkflowView:
        artifact = self._session.scalar(
            select(ReviewArtifactModel).where(ReviewArtifactModel.workflow_run_id == workflow.id)
        )
        return ControlledWorkflowView(
            id=workflow.id,
            claim_id=workflow.claim_id,
            workflow_type=workflow.workflow_type,
            workflow_version=workflow.version,
            status=workflow.status,
            current_stage=workflow.current_stage,
            checkpoint_version=workflow.checkpoint_version,
            task=workflow.task or "Legacy workflow",
            applicable_policy_edition=workflow.applicable_policy_edition or "unknown",
            human_review_required=workflow.human_review_required,
            approval_state=workflow.approval_state,
            retry_count=workflow.retry_count,
            max_retries=workflow.max_retries,
            correlation_id=workflow.correlation_id,
            input_fingerprint=workflow.input_fingerprint or "",
            error_code=workflow.error_code,
            error_detail=workflow.error_detail,
            artifact=ReviewArtifactView.model_validate(artifact.content) if artifact else None,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )

    def _initial_state(self, workflow: WorkflowRunModel, actor: Actor) -> WorkflowState:
        mandatory = self._claims.review_status(workflow.claim_id, actor) in {"open", "assigned"}
        return WorkflowState(
            workflow_id=str(workflow.id),
            workflow_version=workflow.version,
            tenant_id=str(workflow.tenant_id),
            claim_id=str(workflow.claim_id),
            initiating_actor_id=str(actor.user_id),
            correlation_id=workflow.correlation_id,
            current_stage="created",
            status="created",
            task=workflow.task or "",
            retrieved_evidence=[],
            citations=[],
            applicable_policy_edition=workflow.applicable_policy_edition or "unknown",
            conflicts=[],
            ambiguities=[],
            missing_information=[],
            prompt_injection_indicators=[],
            human_review_required=mandatory,
            human_review_reason=None,
            proposed_next_steps=[],
            approval_state="not_required",
            checkpoint_version=0,
            input_fingerprint=workflow.input_fingerprint or "",
            retry_count=workflow.retry_count,
            max_retries=workflow.max_retries,
            error_code=None,
            error_detail=None,
        )

    def _fingerprint(self, claim_id: UUID, actor: Actor, task: str) -> str:
        documents = self._claims.documents(claim_id, actor)
        material = "|".join(sorted(item.checksum_sha256 for item in documents)) + "|" + task
        return hashlib.sha256(material.encode()).hexdigest()

    def _persist(
        self,
        workflow: WorkflowRunModel,
        state: WorkflowState,
        actor_id: UUID | None,
        event_type: str,
        previous_status: str | None,
    ) -> None:
        workflow.checkpoint_version += 1
        state["checkpoint_version"] = workflow.checkpoint_version
        workflow.status = state["status"]
        workflow.current_stage = state["current_stage"]
        workflow.human_review_required = state["human_review_required"]
        workflow.approval_state = state["approval_state"]
        workflow.error_code = state.get("error_code")
        workflow.error_detail = state.get("error_detail")
        workflow.updated_at = datetime.now(UTC)
        self._checkpoint_and_event(workflow, state, actor_id, event_type, previous_status)
        self._session.commit()

    def _checkpoint_and_event(
        self,
        workflow: WorkflowRunModel,
        state: WorkflowState,
        actor_id: UUID | None,
        event_type: str,
        previous_status: str | None,
        details: dict[str, object] | None = None,
    ) -> None:
        sequence = (
            int(
                self._session.scalar(
                    select(func.count())
                    .select_from(WorkflowEventModel)
                    .where(WorkflowEventModel.workflow_run_id == workflow.id)
                )
                or 0
            )
            + 1
        )
        self._session.add(
            WorkflowCheckpointModel(
                workflow_run_id=workflow.id,
                tenant_id=workflow.tenant_id,
                claim_id=workflow.claim_id,
                version=workflow.checkpoint_version,
                stage=state["current_stage"],
                status=state["status"],
                state=dict(state),
                input_fingerprint=state["input_fingerprint"],
            )
        )
        self._session.add(
            WorkflowEventModel(
                workflow_run_id=workflow.id,
                tenant_id=workflow.tenant_id,
                claim_id=workflow.claim_id,
                sequence=sequence,
                actor_user_id=actor_id,
                event_type=event_type,
                previous_status=previous_status,
                new_status=state["status"],
                stage=state["current_stage"],
                details=details
                or {
                    "workflow_version": workflow.version,
                    "checkpoint_version": workflow.checkpoint_version,
                },
                correlation_id=workflow.correlation_id,
            )
        )
        self._audit(workflow, actor_id, event_type, "success")

    def _audit(
        self, workflow: WorkflowRunModel, actor_id: UUID | None, action: str, outcome: str
    ) -> None:
        self._session.add(
            AuditEventModel(
                tenant_id=workflow.tenant_id,
                actor_user_id=actor_id,
                action=action,
                resource_type="workflow",
                resource_id=str(workflow.id),
                outcome=outcome,
                correlation_id=workflow.correlation_id,
                details={
                    "claim_id": str(workflow.claim_id),
                    "workflow_version": workflow.version,
                    "stage": workflow.current_stage,
                    "checkpoint_version": workflow.checkpoint_version,
                },
            )
        )

    def _upsert_artifact(self, workflow: WorkflowRunModel, content: dict[str, object]) -> None:
        artifact = self._session.scalar(
            select(ReviewArtifactModel).where(ReviewArtifactModel.workflow_run_id == workflow.id)
        )
        if artifact is None:
            self._session.add(
                ReviewArtifactModel(
                    workflow_run_id=workflow.id,
                    tenant_id=workflow.tenant_id,
                    claim_id=workflow.claim_id,
                    content=content,
                )
            )
        else:
            artifact.version += 1
            artifact.content = content
            artifact.updated_at = datetime.now(UTC)

    def _upsert_review_task(self, workflow: WorkflowRunModel, state: WorkflowState) -> None:
        task = self._session.scalar(
            select(HumanReviewTaskModel).where(HumanReviewTaskModel.workflow_run_id == workflow.id)
        )
        if task is None:
            self._session.add(
                HumanReviewTaskModel(
                    tenant_id=workflow.tenant_id,
                    claim_id=workflow.claim_id,
                    workflow_run_id=workflow.id,
                    status="open",
                    reason_code="phase4_workflow_review",
                    reason=state["human_review_reason"]
                    or "Human review required by workflow policy.",
                )
            )

    def _state_from_checkpoint(self, workflow: WorkflowRunModel) -> WorkflowState:
        checkpoint = self._session.scalar(
            select(WorkflowCheckpointModel)
            .where(WorkflowCheckpointModel.workflow_run_id == workflow.id)
            .order_by(WorkflowCheckpointModel.version.desc())
            .limit(1)
        )
        if checkpoint is None:
            raise WorkflowConflictError("workflow has no resumable checkpoint")
        return cast(WorkflowState, checkpoint.state)
