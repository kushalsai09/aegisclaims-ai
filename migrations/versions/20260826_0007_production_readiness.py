"""Add OIDC transaction state and measured operational indexes.

Revision ID: 20260826_0007
Revises: 20260826_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0007"
down_revision: str | None = "20260826_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oidc_login_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("state_hash", sa.String(64), nullable=False),
        sa.Column("nonce_hash", sa.String(64), nullable=False),
        sa.Column("browser_binding_hash", sa.String(64), nullable=False),
        sa.Column("code_verifier", sa.String(128), nullable=False),
        sa.Column("redirect_uri", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_oidc_login_transactions_state_hash",
        "oidc_login_transactions",
        ["state_hash"],
        unique=True,
    )
    op.create_index(
        "ix_oidc_login_transactions_expires_at",
        "oidc_login_transactions",
        ["expires_at"],
    )
    op.create_index("ix_claims_tenant_updated", "claims", ["tenant_id", "updated_at"])
    op.create_index(
        "ix_claim_assignments_actor_claim",
        "claim_assignments",
        ["tenant_id", "user_id", "claim_id"],
    )
    op.create_index(
        "ix_documents_tenant_claim_created",
        "documents",
        ["tenant_id", "claim_id", "created_at"],
    )
    op.create_index(
        "ix_workflow_runs_tenant_claim_created",
        "workflow_runs",
        ["tenant_id", "claim_id", "created_at"],
    )
    op.create_index(
        "ix_review_tasks_tenant_status_created",
        "human_review_tasks",
        ["tenant_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_review_tasks_tenant_status_created", table_name="human_review_tasks")
    op.drop_index("ix_workflow_runs_tenant_claim_created", table_name="workflow_runs")
    op.drop_index("ix_documents_tenant_claim_created", table_name="documents")
    op.drop_index("ix_claim_assignments_actor_claim", table_name="claim_assignments")
    op.drop_index("ix_claims_tenant_updated", table_name="claims")
    op.drop_table("oidc_login_transactions")
