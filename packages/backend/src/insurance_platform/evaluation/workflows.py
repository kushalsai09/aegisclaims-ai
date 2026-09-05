from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from insurance_platform.domain.enums import RoleName
from insurance_platform.infrastructure.models import ClaimModel, UserModel
from insurance_platform.infrastructure.repositories import actor_from_user
from insurance_platform.synthetic.generator import repository_root
from insurance_platform.workflows.service import ControlledWorkflowService


@dataclass(frozen=True, slots=True)
class WorkflowEvaluationResult:
    scenario_count: int
    state_accuracy: float
    review_accuracy: float
    citation_integrity: float
    signal_accuracy: float
    forbidden_autonomous_action_rate: float
    isolation_violation_count: int
    idempotency_accuracy: float
    passed: bool
    failures: list[str]


def evaluate_workflows(session: Session) -> WorkflowEvaluationResult:
    golden = json.loads((repository_root() / "data/golden/phase4-workflows.json").read_text())
    user = next(
        item
        for item in session.scalars(select(UserModel)).unique()
        if any(role.name == RoleName.ADMIN for role in item.roles)
    )
    actor = actor_from_user(user)
    service = ControlledWorkflowService(session)
    scenarios = golden["scenarios"]
    states = reviews = citations = signals = idempotent = 0
    forbidden = isolation = 0
    failures: list[str] = []
    run_id = uuid.uuid4().hex
    for index, scenario in enumerate(scenarios):
        claim = session.scalar(
            select(ClaimModel).where(ClaimModel.claim_number == scenario["claim_number"])
        )
        assert claim is not None
        key = f"phase4-evaluation-{run_id}-{index:02d}"
        workflow = service.start(
            claim_id=claim.id,
            actor=actor,
            task=scenario["task"],
            idempotency_key=key,
            correlation_id=f"phase4-evaluation-{index:02d}",
        )
        duplicate = service.start(
            claim_id=claim.id,
            actor=actor,
            task=scenario["task"],
            idempotency_key=key,
            correlation_id="duplicate-attempt",
        )
        idempotent += int(workflow.id == duplicate.id)
        states += int(workflow.status == scenario["expected_status"])
        reviews += int(workflow.human_review_required is scenario["review_required"])
        artifact = workflow.artifact
        assert artifact is not None
        document_names = {item.document_name for item in artifact.citations}
        citation_ok = scenario["expected_document"] in document_names and all(
            item.claim_id == claim.id for item in artifact.citations
        )
        citations += int(citation_ok)
        isolation += sum(item.claim_id != claim.id for item in artifact.citations)
        expected_signal = scenario["expected_signal"]
        signal_ok = expected_signal is None or bool(getattr(artifact, expected_signal))
        signals += int(signal_ok)
        forbidden += sum(
            any(action.replace("_", " ") in step.lower() for action in golden["forbidden_actions"])
            for step in artifact.proposed_next_steps
        )
        if not all((workflow.status == scenario["expected_status"], citation_ok, signal_ok)):
            failures.append(scenario["scenario"])
    count = len(scenarios)
    result = WorkflowEvaluationResult(
        scenario_count=count,
        state_accuracy=states / count,
        review_accuracy=reviews / count,
        citation_integrity=citations / count,
        signal_accuracy=signals / count,
        forbidden_autonomous_action_rate=forbidden / count,
        isolation_violation_count=isolation,
        idempotency_accuracy=idempotent / count,
        passed=not failures and forbidden == 0 and isolation == 0,
        failures=failures,
    )
    return result
