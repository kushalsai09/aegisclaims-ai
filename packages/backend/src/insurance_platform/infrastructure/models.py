from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from insurance_platform.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Uuid, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class TenantModel(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RoleModel(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str] = mapped_column(String(240))


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "subject", name="uq_users_tenant_subject"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    subject: Mapped[str] = mapped_column(String(180))
    first_name: Mapped[str] = mapped_column(String(80), default="")
    last_name: Mapped[str] = mapped_column(String(80), default="")
    display_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str | None] = mapped_column(String(512))
    account_status: Mapped[str] = mapped_column(String(40), default="active")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    roles: Mapped[list[RoleModel]] = relationship(secondary=user_roles, lazy="selectin")


class UserSessionModel(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[UserModel] = relationship(lazy="joined")


class OIDCLoginTransactionModel(Base):
    __tablename__ = "oidc_login_transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    nonce_hash: Mapped[str] = mapped_column(String(64))
    browser_binding_hash: Mapped[str] = mapped_column(String(64))
    code_verifier: Mapped[str] = mapped_column(String(128))
    redirect_uri: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PolicyModel(Base):
    __tablename__ = "policies"
    __table_args__ = (UniqueConstraint("tenant_id", "policy_number", name="uq_policy_number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    policy_number: Mapped[str] = mapped_column(String(80))
    product_code: Mapped[str] = mapped_column(String(80))
    product_name: Mapped[str] = mapped_column(String(160))
    edition: Mapped[str] = mapped_column(String(80))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="active")
    synthetic_label: Mapped[str] = mapped_column(String(80))


class ClaimModel(Base):
    __tablename__ = "claims"
    __table_args__ = (UniqueConstraint("tenant_id", "claim_number", name="uq_claim_number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    policy_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("policies.id"), index=True)
    claim_number: Mapped[str] = mapped_column(String(80))
    loss_date: Mapped[date] = mapped_column(Date)
    loss_type: Mapped[str] = mapped_column(String(80))
    property_address: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(40), default="open")
    description: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    policy: Mapped[PolicyModel] = relationship(lazy="joined")


class ClaimAssignmentModel(Base):
    __tablename__ = "claim_assignments"
    __table_args__ = (UniqueConstraint("claim_id", "user_id", name="uq_claim_assignment"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    assignment_type: Mapped[str] = mapped_column(String(40), default="assigned")


class DocumentModel(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "claim_id", "checksum_sha256", name="uq_document_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id"), index=True)
    name: Mapped[str] = mapped_column(String(240))
    original_filename: Mapped[str] = mapped_column(String(240), default="")
    document_type: Mapped[str] = mapped_column(String(80))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    normalized_storage_key: Mapped[str | None] = mapped_column(String(500))
    extraction_artifact_key: Mapped[str | None] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(120))
    detected_mime_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(default=0)
    processing_status: Mapped[str] = mapped_column(String(40), default="uploaded")
    extraction_status: Mapped[str] = mapped_column(String(40), default="pending")
    page_count: Mapped[int] = mapped_column(default=0)
    classification_method: Mapped[str | None] = mapped_column(String(80))
    classification_version: Mapped[str | None] = mapped_column(String(40))
    classification_signals: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    injection_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), index=True
    )
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_detail: Mapped[str | None] = mapped_column(String(500))
    synthetic_label: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    uploaded_by: Mapped[UserModel | None] = relationship(lazy="joined")
    pages: Mapped[list[DocumentPageModel]] = relationship(
        back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )
    facts: Mapped[list[DocumentFactModel]] = relationship(
        back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )
    processing_events: Mapped[list[DocumentProcessingEventModel]] = relationship(
        back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )


class DocumentPageModel(Base):
    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_number", name="uq_document_page"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    text_sha256: Mapped[str] = mapped_column(String(64))
    extraction_method: Mapped[str] = mapped_column(String(80))
    extraction_version: Mapped[str] = mapped_column(String(40))
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    document: Mapped[DocumentModel] = relationship(back_populates="pages")


class DocumentFactModel(Base):
    __tablename__ = "document_facts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer)
    fact_type: Mapped[str] = mapped_column(String(100), index=True)
    raw_source_span: Mapped[str] = mapped_column(Text)
    normalized_value: Mapped[str] = mapped_column(Text)
    extraction_method: Mapped[str] = mapped_column(String(80))
    extraction_version: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    document: Mapped[DocumentModel] = relationship(back_populates="facts")


class FactConflictModel(Base):
    __tablename__ = "fact_conflicts"
    __table_args__ = (
        UniqueConstraint(
            "claim_id", "fact_type", "left_fact_id", "right_fact_id", name="uq_fact_conflict"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id"), index=True)
    fact_type: Mapped[str] = mapped_column(String(100))
    left_fact_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("document_facts.id"))
    right_fact_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("document_facts.id"))
    status: Mapped[str] = mapped_column(String(40), default="conflict_detected")
    detection_method: Mapped[str] = mapped_column(String(80), default="deterministic_exact_v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    left_fact: Mapped[DocumentFactModel] = relationship(foreign_keys=[left_fact_id], lazy="joined")
    right_fact: Mapped[DocumentFactModel] = relationship(
        foreign_keys=[right_fact_id], lazy="joined"
    )


class DocumentProcessingEventModel(Base):
    __tablename__ = "document_processing_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str] = mapped_column(String(500))
    correlation_id: Mapped[str] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    document: Mapped[DocumentModel] = relationship(back_populates="processing_events")


class DocumentIndexModel(Base):
    __tablename__ = "document_indexes"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "source_checksum",
            "chunker_version",
            "embedding_version",
            name="uq_document_index_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    source_checksum: Mapped[str] = mapped_column(String(64))
    chunker_version: Mapped[str] = mapped_column(String(80))
    embedding_provider: Mapped[str] = mapped_column(String(80))
    embedding_model: Mapped[str] = mapped_column(String(120))
    embedding_version: Mapped[str] = mapped_column(String(80))
    embedding_dimensions: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40), default="indexing")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RetrievalChunkModel(Base):
    __tablename__ = "retrieval_chunks"
    __table_args__ = (
        UniqueConstraint("chunk_identifier", name="uq_retrieval_chunk_identifier"),
        UniqueConstraint("index_id", "chunk_ordinal", name="uq_retrieval_index_ordinal"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    index_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("document_indexes.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("document_pages.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer)
    chunk_identifier: Mapped[str] = mapped_column(String(80), index=True)
    chunk_ordinal: Mapped[int] = mapped_column(Integer)
    document_type: Mapped[str] = mapped_column(String(80))
    policy_edition: Mapped[str | None] = mapped_column(String(80), index=True)
    source_checksum: Mapped[str] = mapped_column(String(64))
    page_checksum: Mapped[str] = mapped_column(String(64))
    normalized_text: Mapped[str] = mapped_column(Text)
    source_start: Mapped[int] = mapped_column(Integer)
    source_end: Mapped[int] = mapped_column(Integer)
    chunker_version: Mapped[str] = mapped_column(String(80))
    embedding_provider: Mapped[str] = mapped_column(String(80))
    embedding_model: Mapped[str] = mapped_column(String(120))
    embedding_version: Mapped[str] = mapped_column(String(80))
    embedding: Mapped[list[float]] = mapped_column(JSON)
    injection_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    document: Mapped[DocumentModel] = relationship(lazy="joined")


class WorkflowRunModel(Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "claim_id", "idempotency_key", name="uq_workflow_start_idempotency"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id"), index=True)
    workflow_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(40))
    version: Mapped[str] = mapped_column(String(40))
    correlation_id: Mapped[str] = mapped_column(String(100))
    initiating_actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    task: Mapped[str | None] = mapped_column(String(500))
    current_stage: Mapped[str] = mapped_column(String(80), default="created")
    checkpoint_version: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str | None] = mapped_column(String(100))
    input_fingerprint: Mapped[str | None] = mapped_column(String(64))
    applicable_policy_edition: Mapped[str | None] = mapped_column(String(80))
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_state: Mapped[str] = mapped_column(String(40), default="not_required")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=2)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_detail: Mapped[str | None] = mapped_column(String(500))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class HumanReviewTaskModel(Base):
    __tablename__ = "human_review_tasks"
    __table_args__ = (UniqueConstraint("workflow_run_id", name="uq_review_task_workflow"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id"), index=True)
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id"), index=True
    )
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(40))
    reason_code: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkflowCheckpointModel(Base):
    __tablename__ = "workflow_checkpoints"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "version", name="uq_workflow_checkpoint_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    stage: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40))
    state: Mapped[dict[str, Any]] = mapped_column(JSON)
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class WorkflowEventModel(Base):
    __tablename__ = "workflow_events"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "sequence", name="uq_workflow_event_sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    previous_status: Mapped[str | None] = mapped_column(String(40))
    new_status: Mapped[str] = mapped_column(String(40))
    stage: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    correlation_id: Mapped[str] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ReviewArtifactModel(Base):
    __tablename__ = "review_artifacts"
    __table_args__ = (UniqueConstraint("workflow_run_id", name="uq_review_artifact_workflow"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ModelInvocationModel(Base):
    __tablename__ = "model_invocations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id"), index=True)
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id"), index=True
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80))
    model_identifier: Mapped[str] = mapped_column(String(120))
    configuration_version: Mapped[str] = mapped_column(String(80))
    prompt_template_version: Mapped[str] = mapped_column(String(80))
    retrieval_configuration: Mapped[str] = mapped_column(String(80))
    response_schema_version: Mapped[str] = mapped_column(String(80))
    evidence_fingerprint: Mapped[str] = mapped_column(String(64))
    authorized_citation_ids: Mapped[list[str]] = mapped_column(JSON)
    prompt_hash: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(40))
    validation_failures: Mapped[list[str]] = mapped_column(JSON, default=list)
    latency_ms: Mapped[float | None]
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    correlation_id: Mapped[str] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ClaimEvidenceBriefModel(Base):
    __tablename__ = "claim_evidence_briefs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "claim_id", "idempotency_key", name="uq_brief_idempotency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id"), index=True)
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id"), index=True
    )
    invocation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("model_invocations.id"), unique=True, index=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    task: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(40))
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    evidence_fingerprint: Mapped[str] = mapped_column(String(64))
    applicable_policy_edition: Mapped[str] = mapped_column(String(80))
    idempotency_key: Mapped[str] = mapped_column(String(100))
    validation_state: Mapped[str] = mapped_column(String(40), default="valid")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class WorkflowReviewActionModel(Base):
    __tablename__ = "workflow_review_actions"
    __table_args__ = (
        UniqueConstraint(
            "workflow_run_id", "idempotency_key", name="uq_workflow_review_idempotency"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(String(500))
    expected_checkpoint_version: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(120), index=True)
    resource_type: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str] = mapped_column(String(100))
    outcome: Mapped[str] = mapped_column(String(40))
    correlation_id: Mapped[str] = mapped_column(String(100), index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
