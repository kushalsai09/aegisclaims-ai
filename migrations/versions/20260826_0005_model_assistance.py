"""Add governed model invocations and claim evidence briefs.

Revision ID: 20260826_0005
Revises: 20260826_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0005"
down_revision: str | None = "20260826_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_invocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid()),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("model_identifier", sa.String(120), nullable=False),
        sa.Column("configuration_version", sa.String(80), nullable=False),
        sa.Column("prompt_template_version", sa.String(80), nullable=False),
        sa.Column("retrieval_configuration", sa.String(80), nullable=False),
        sa.Column("response_schema_version", sa.String(80), nullable=False),
        sa.Column("evidence_fingerprint", sa.String(64), nullable=False),
        sa.Column("authorized_citation_ids", sa.JSON(), nullable=False),
        sa.Column("prompt_hash", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(40), nullable=False),
        sa.Column("validation_failures", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Float()),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "claim_evidence_briefs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid()),
        sa.Column("invocation_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("task", sa.String(500), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("evidence_fingerprint", sa.String(64), nullable=False),
        sa.Column("applicable_policy_edition", sa.String(80), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("validation_state", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["invocation_id"], ["model_invocations.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invocation_id"),
        sa.UniqueConstraint(
            "tenant_id", "claim_id", "idempotency_key", name="uq_brief_idempotency"
        ),
    )
    for table in ("model_invocations", "claim_evidence_briefs"):
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        op.create_index(f"ix_{table}_claim_id", table, ["claim_id"])
        op.create_index(f"ix_{table}_workflow_run_id", table, ["workflow_run_id"])
    op.create_index("ix_model_invocations_actor_user_id", "model_invocations", ["actor_user_id"])
    op.create_index("ix_model_invocations_correlation_id", "model_invocations", ["correlation_id"])
    op.create_index(
        "ix_claim_evidence_briefs_invocation_id", "claim_evidence_briefs", ["invocation_id"]
    )


def downgrade() -> None:
    op.drop_table("claim_evidence_briefs")
    op.drop_table("model_invocations")
