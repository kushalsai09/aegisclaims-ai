from __future__ import annotations

from insurance_platform.domain.entities import Actor
from insurance_platform.domain.enums import Action, RoleName

ROLE_PERMISSIONS: dict[RoleName, frozenset[Action]] = {
    RoleName.CLAIMS_ADJUSTER: frozenset(
        {
            Action.DASHBOARD_READ,
            Action.CLAIM_READ,
            Action.DOCUMENT_READ,
            Action.DOCUMENT_UPLOAD,
            Action.RETRIEVAL_QUERY,
            Action.WORKFLOW_START,
            Action.WORKFLOW_READ,
            Action.WORKFLOW_CANCEL,
            Action.BRIEF_CREATE,
            Action.BRIEF_READ,
        }
    ),
    RoleName.SUPERVISOR: frozenset(
        {
            Action.DASHBOARD_READ,
            Action.CLAIM_READ,
            Action.DOCUMENT_READ,
            Action.DOCUMENT_UPLOAD,
            Action.RETRIEVAL_QUERY,
            Action.REVIEW_QUEUE_READ,
            Action.WORKFLOW_START,
            Action.WORKFLOW_READ,
            Action.WORKFLOW_REVIEW,
            Action.WORKFLOW_RETRY,
            Action.WORKFLOW_CANCEL,
            Action.BRIEF_CREATE,
            Action.BRIEF_READ,
        }
    ),
    RoleName.COMPLIANCE_REVIEWER: frozenset(
        {
            Action.DASHBOARD_READ,
            Action.CLAIM_READ,
            Action.DOCUMENT_READ,
            Action.RETRIEVAL_QUERY,
            Action.OPERATIONS_READ,
            Action.WORKFLOW_READ,
            Action.BRIEF_READ,
        }
    ),
    RoleName.ADMIN: frozenset(Action),
}


class AuthorizationError(Exception):
    def __init__(self, action: Action) -> None:
        super().__init__(f"actor is not permitted to perform {action}")
        self.action = action


def authorize(actor: Actor, action: Action) -> None:
    allowed = any(action in ROLE_PERMISSIONS[role] for role in actor.roles)
    if not allowed:
        raise AuthorizationError(action)
