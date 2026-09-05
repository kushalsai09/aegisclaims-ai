"""Add controlled workflow orchestration and durable review checkpoints.

Revision ID: 20260826_0004
Revises: 20260826_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0004"
down_revision: str | None = "20260826_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("workflow_runs") as batch:
        batch.add_column(sa.Column("initiating_actor_id", sa.Uuid()))
        batch.add_column(sa.Column("task", sa.String(500)))
        batch.add_column(
            sa.Column("current_stage", sa.String(80), nullable=False, server_default="created")
        )
        batch.add_column(
            sa.Column("checkpoint_version", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("idempotency_key", sa.String(100)))
        batch.add_column(sa.Column("input_fingerprint", sa.String(64)))
        batch.add_column(sa.Column("applicable_policy_edition", sa.String(80)))
        batch.add_column(
            sa.Column(
                "human_review_required", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
        batch.add_column(
            sa.Column(
                "approval_state", sa.String(40), nullable=False, server_default="not_required"
            )
        )
        batch.add_column(sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2"))
        batch.add_column(sa.Column("error_code", sa.String(100)))
        batch.add_column(sa.Column("error_detail", sa.String(500)))
        batch.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            )
        )
        batch.create_foreign_key("fk_workflow_actor", "users", ["initiating_actor_id"], ["id"])
        batch.create_unique_constraint(
            "uq_workflow_start_idempotency", ["tenant_id", "claim_id", "idempotency_key"]
        )

    with op.batch_alter_table("human_review_tasks") as batch:
        batch.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            )
        )
        batch.add_column(sa.Column("completed_at", sa.DateTime(timezone=True)))
        batch.create_unique_constraint("uq_review_task_workflow", ["workflow_run_id"])

    op.create_table(
        "workflow_checkpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_run_id", "version", name="uq_workflow_checkpoint_version"),
    )
    op.create_table(
        "workflow_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid()),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("previous_status", sa.String(40)),
        sa.Column("new_status", sa.String(40), nullable=False),
        sa.Column("stage", sa.String(80), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_run_id", "sequence", name="uq_workflow_event_sequence"),
    )
    op.create_table(
        "review_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_run_id", name="uq_review_artifact_workflow"),
    )
    op.create_table(
        "workflow_review_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("expected_checkpoint_version", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workflow_run_id", "idempotency_key", name="uq_workflow_review_idempotency"
        ),
    )
    for table in (
        "workflow_checkpoints",
        "workflow_events",
        "review_artifacts",
        "workflow_review_actions",
    ):
        op.create_index(f"ix_{table}_workflow_run_id", table, ["workflow_run_id"])
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
    op.create_index("ix_workflow_checkpoints_claim_id", "workflow_checkpoints", ["claim_id"])
    op.create_index("ix_workflow_events_claim_id", "workflow_events", ["claim_id"])
    op.create_index("ix_workflow_events_event_type", "workflow_events", ["event_type"])
    op.create_index("ix_workflow_events_correlation_id", "workflow_events", ["correlation_id"])
    op.create_index("ix_review_artifacts_claim_id", "review_artifacts", ["claim_id"])
    op.create_index(
        "ix_workflow_review_actions_actor_user_id", "workflow_review_actions", ["actor_user_id"]
    )


def downgrade() -> None:
    op.drop_table("workflow_review_actions")
    op.drop_table("review_artifacts")
    op.drop_table("workflow_events")
    op.drop_table("workflow_checkpoints")
    with op.batch_alter_table("human_review_tasks") as batch:
        batch.drop_constraint("uq_review_task_workflow", type_="unique")
        batch.drop_column("completed_at")
        batch.drop_column("updated_at")
    with op.batch_alter_table("workflow_runs") as batch:
        batch.drop_constraint("uq_workflow_start_idempotency", type_="unique")
        batch.drop_constraint("fk_workflow_actor", type_="foreignkey")
        for column in (
            "updated_at",
            "error_detail",
            "error_code",
            "max_retries",
            "retry_count",
            "approval_state",
            "human_review_required",
            "applicable_policy_edition",
            "input_fingerprint",
            "idempotency_key",
            "checkpoint_version",
            "current_stage",
            "task",
            "initiating_actor_id",
        ):
            batch.drop_column(column)
