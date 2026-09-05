from __future__ import annotations

from typing import NotRequired, TypedDict


class WorkflowState(TypedDict):
    workflow_id: str
    workflow_version: str
    tenant_id: str
    claim_id: str
    initiating_actor_id: str
    correlation_id: str
    current_stage: str
    status: str
    task: str
    retrieved_evidence: list[dict[str, object]]
    citations: list[dict[str, object]]
    applicable_policy_edition: str
    conflicts: list[dict[str, object]]
    ambiguities: list[str]
    missing_information: list[str]
    prompt_injection_indicators: list[str]
    human_review_required: bool
    human_review_reason: str | None
    proposed_next_steps: list[str]
    approval_state: str
    checkpoint_version: int
    input_fingerprint: str
    retry_count: int
    max_retries: int
    error_code: NotRequired[str | None]
    error_detail: NotRequired[str | None]


WORKFLOW_VERSION = "phase4-claim-evidence-review-v1"
FORBIDDEN_ACTIONS = [
    "approve_or_deny_claim",
    "determine_coverage_or_liability",
    "determine_fraud",
    "calculate_or_issue_payment",
    "modify_policy_or_source_documents",
    "contact_external_parties",
    "close_claim",
    "invoke_shell_filesystem_sql_http_or_browser_tools",
]
