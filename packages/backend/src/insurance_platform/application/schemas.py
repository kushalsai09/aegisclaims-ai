from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RoleView(ApiModel):
    name: str


class UserView(ApiModel):
    id: UUID
    first_name: str = ""
    last_name: str = ""
    display_name: str
    email: str
    roles: list[str]
    organization: str = ""
    account_status: str = "active"
    created_at: datetime | None = None
    last_login_at: datetime | None = None


class SessionRequest(ApiModel):
    user_id: UUID


class SessionView(ApiModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserView


class LoginRequest(ApiModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)
    remember: bool = False


class AuthenticatedSessionView(ApiModel):
    user: UserView
    expires_at: datetime


class PolicyView(ApiModel):
    id: UUID
    policy_number: str
    product_code: str
    product_name: str
    edition: str
    effective_from: date
    effective_to: date
    status: str
    synthetic_label: str


class ClaimSummaryView(ApiModel):
    id: UUID
    claim_number: str
    loss_date: date
    loss_type: str
    property_address: str
    status: str
    policy_number: str
    workflow_status: str
    assigned_to: str | None = None
    updated_at: datetime


class ClaimView(ApiModel):
    id: UUID
    claim_number: str
    loss_date: date
    loss_type: str
    property_address: str
    status: str
    description: str
    version: int


class DocumentView(ApiModel):
    id: UUID
    name: str
    document_type: str
    content_type: str
    detected_mime_type: str
    processing_status: str
    extraction_status: str
    page_count: int
    size_bytes: int
    checksum_sha256: str
    uploaded_by: str | None
    uploaded_at: datetime
    injection_risk: bool
    synthetic_label: str
    created_at: datetime


class DocumentPageView(ApiModel):
    page_number: int
    text: str
    text_sha256: str
    extraction_method: str
    extraction_version: str
    extracted_at: datetime


class DocumentFactView(ApiModel):
    id: UUID
    page_number: int
    fact_type: str
    raw_source_span: str
    normalized_value: str
    extraction_method: str
    extraction_version: str


class ProcessingEventView(ApiModel):
    status: str
    detail: str
    correlation_id: str
    created_at: datetime


class FactConflictView(ApiModel):
    id: UUID
    fact_type: str
    status: str
    detection_method: str
    left_document_name: str
    right_document_name: str
    left: DocumentFactView
    right: DocumentFactView


class DocumentDetailView(ApiModel):
    document: DocumentView
    pages: list[DocumentPageView]
    facts: list[DocumentFactView]
    conflicts: list[FactConflictView]
    processing_history: list[ProcessingEventView]
    error_code: str | None
    error_detail: str | None


class WorkflowView(ApiModel):
    id: UUID
    workflow_type: str
    status: str
    version: str
    created_at: datetime


class FutureSectionView(ApiModel):
    key: str
    title: str
    status: Literal["not_implemented"] = "not_implemented"
    description: str


class ClaimWorkspaceView(ApiModel):
    claim: ClaimView
    policy: PolicyView
    documents: list[DocumentView]
    conflicts: list[FactConflictView]
    workflow: WorkflowView | None
    human_review_status: str
    future_sections: list[FutureSectionView]
    synthetic_notice: str


class DashboardView(ApiModel):
    assigned_claims: int
    open_reviews: int
    platform_status: Literal["operational"] = "operational"
    implementation_phase: Literal["phase_7_production_readiness"] = "phase_7_production_readiness"


class EvidenceQuery(ApiModel):
    question: str = Field(min_length=3, max_length=500)
    limit: int = Field(default=5, ge=1, le=10)


class CitationView(ApiModel):
    id: str
    claim_id: UUID
    document_id: UUID
    document_name: str
    document_type: str
    page_number: int
    chunk_identifier: str
    chunk_ordinal: int
    source_start: int
    source_end: int
    source_checksum: str
    page_checksum: str
    excerpt: str
    policy_edition: str | None
    applicability_status: str
    injection_risk: bool
    retrieval_rank: int
    retrieval_score: float
    lexical_score: float
    vector_score: float
    retrieval_method: str
    source_url: str


class EvidenceSearchView(ApiModel):
    question: str
    citations: list[CitationView]
    retrieval_configuration: str
    embedding_provider: str
    embedding_model: str
    embedding_version: str
    candidate_chunks: int
    returned_chunks: int
    retrieval_duration_ms: float
    embedding_duration_ms: float
    correlation_id: str


class ConflictSummaryView(ApiModel):
    fact_type: str
    left_document_name: str
    left_value: str
    right_document_name: str
    right_value: str


class GroundedAnswerView(ApiModel):
    question: str
    state: Literal[
        "answerable", "insufficient_evidence", "conflicting_evidence", "ambiguous_evidence"
    ]
    answer: str
    answerable: bool
    citations: list[CitationView]
    retrieved_evidence: list[CitationView]
    conflicts: list[ConflictSummaryView]
    ambiguity_indicators: list[str]
    missing_information: list[str]
    human_review_required: bool
    applicable_policy_version: str
    retrieval_configuration: str
    generator_provider: str
    generator_model: str
    generator_version: str
    retrieval_duration_ms: float
    embedding_duration_ms: float
    generation_duration_ms: float
    correlation_id: str


class ReviewTaskView(ApiModel):
    id: UUID
    claim_id: UUID
    status: str
    reason_code: str
    reason: str
    created_at: datetime
    workflow_id: UUID | None = None
    workflow_status: str | None = None
    safety_flags: list[str] = Field(default_factory=list)
    claim_number: str | None = None
    assigned_to: str | None = None


class WorkflowStartRequest(ApiModel):
    task: str = Field(min_length=3, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")


class WorkflowReviewRequest(ApiModel):
    action: Literal[
        "acknowledge",
        "approve_proposed_next_step",
        "reject_proposal",
        "request_more_information",
        "return_for_evidence_review",
    ]
    reason: str = Field(min_length=3, max_length=500)
    expected_checkpoint_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")


class WorkflowRetryRequest(ApiModel):
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")


class WorkflowEventView(ApiModel):
    sequence: int
    event_type: str
    previous_status: str | None
    new_status: str
    stage: str
    actor_user_id: UUID | None
    details: dict[str, object]
    correlation_id: str
    created_at: datetime


class ReviewArtifactView(ApiModel):
    established_evidence: list[dict[str, object]]
    applicable_policy_evidence: list[dict[str, object]]
    conflicting_evidence: list[dict[str, object]]
    ambiguous_evidence: list[str]
    missing_information: list[str]
    untrusted_content_flags: list[str]
    proposed_next_steps: list[str]
    human_review_reason: str | None
    citations: list[CitationView]
    authority_notice: str
    forbidden_actions: list[str]


class ControlledWorkflowView(ApiModel):
    id: UUID
    claim_id: UUID
    workflow_type: str
    workflow_version: str
    status: str
    current_stage: str
    checkpoint_version: int
    task: str
    applicable_policy_edition: str
    human_review_required: bool
    approval_state: str
    retry_count: int
    max_retries: int
    correlation_id: str
    input_fingerprint: str
    error_code: str | None
    error_detail: str | None
    artifact: ReviewArtifactView | None
    created_at: datetime
    updated_at: datetime


class WorkflowHistoryView(ApiModel):
    workflow_id: UUID
    events: list[WorkflowEventView]


class ClaimEvidenceBriefRequest(ApiModel):
    task: str = Field(min_length=3, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")


class ClaimEvidenceBriefView(ApiModel):
    id: UUID
    claim_id: UUID
    workflow_id: UUID | None
    task: str
    status: Literal[
        "supported", "insufficient_evidence", "conflicting_evidence", "ambiguous_evidence"
    ]
    claim_summary: str
    evidence_summary: str
    applicable_policy_summary: str
    missing_information: list[str]
    conflicts: list[str]
    ambiguities: list[str]
    safety_flags: list[str]
    citations: list[CitationView]
    human_review_required: bool
    limitations: list[str]
    authority_notice: str
    stale: bool
    validation_state: str
    evidence_fingerprint: str
    applicable_policy_edition: str
    provider: str
    model_identifier: str
    configuration_version: str
    prompt_template_version: str
    retrieval_configuration: str
    response_schema_version: str
    latency_ms: float | None
    input_tokens: int | None
    output_tokens: int | None
    retry_count: int
    correlation_id: str
    created_at: datetime


class OperationsSummaryView(ApiModel):
    claim_count: int
    document_count: int
    workflow_count: int
    review_count: int
    ai_metrics_status: Literal["deterministic_model_assistance"] = "deterministic_model_assistance"


class SmokeJobRequest(ApiModel):
    message: str = Field(min_length=1, max_length=120)


class JobView(ApiModel):
    id: str
    status: str
    result: dict[str, object] | None = None


class HealthView(ApiModel):
    status: str
    version: str
    environment: str
    checks: dict[str, str] | None = None
