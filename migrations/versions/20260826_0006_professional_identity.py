"""Add professional local accounts and revocable sessions.

Revision ID: 20260826_0006
Revises: 20260826_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0006"
down_revision: str | None = "20260826_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("first_name", sa.String(80), nullable=False, server_default=""))
        batch.add_column(sa.Column("last_name", sa.String(80), nullable=False, server_default=""))
        batch.add_column(sa.Column("password_hash", sa.String(512)))
        batch.add_column(
            sa.Column("account_status", sa.String(40), nullable=False, server_default="active")
        )
        batch.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True)))
        batch.create_unique_constraint("uq_users_tenant_email", ["tenant_id", "email"])

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_user_sessions_tenant_id", "user_sessions", ["tenant_id"])
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_table("user_sessions")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_tenant_email", type_="unique")
        batch.drop_column("last_login_at")
        batch.drop_column("account_status")
        batch.drop_column("password_hash")
        batch.drop_column("last_name")
        batch.drop_column("first_name")
