"""Add secure document-ingestion metadata and provenance.

Revision ID: 20260826_0002
Revises: 20260826_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0002"
down_revision: str | None = "20260826_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch:
        batch.add_column(
            sa.Column("original_filename", sa.String(240), nullable=False, server_default="")
        )
        batch.add_column(sa.Column("normalized_storage_key", sa.String(500)))
        batch.add_column(sa.Column("extraction_artifact_key", sa.String(500)))
        batch.add_column(
            sa.Column(
                "detected_mime_type",
                sa.String(120),
                nullable=False,
                server_default="application/octet-stream",
            )
        )
        batch.add_column(sa.Column("checksum_sha256", sa.String(64)))
        batch.add_column(sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(
            sa.Column("extraction_status", sa.String(40), nullable=False, server_default="pending")
        )
        batch.add_column(sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("classification_method", sa.String(80)))
        batch.add_column(sa.Column("classification_version", sa.String(40)))
        batch.add_column(
            sa.Column("classification_signals", sa.JSON(), nullable=False, server_default="{}")
        )
        batch.add_column(
            sa.Column("injection_risk", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(sa.Column("uploaded_by_user_id", sa.Uuid()))
        batch.add_column(sa.Column("error_code", sa.String(100)))
        batch.add_column(sa.Column("error_detail", sa.String(500)))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True)))
        batch.create_foreign_key(
            "fk_documents_uploaded_by_user", "users", ["uploaded_by_user_id"], ["id"]
        )
        batch.create_unique_constraint(
            "uq_document_hash", ["tenant_id", "claim_id", "checksum_sha256"]
        )
        batch.create_index("ix_documents_checksum_sha256", ["checksum_sha256"])
        batch.create_index("ix_documents_uploaded_by_user_id", ["uploaded_by_user_id"])

    op.create_table(
        "document_pages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("extraction_method", sa.String(80), nullable=False),
        sa.Column("extraction_version", sa.String(40), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "page_number", name="uq_document_page"),
    )
    op.create_index("ix_document_pages_document_id", "document_pages", ["document_id"])
    op.create_index("ix_document_pages_tenant_id", "document_pages", ["tenant_id"])

    op.create_table(
        "document_facts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("fact_type", sa.String(100), nullable=False),
        sa.Column("raw_source_span", sa.Text(), nullable=False),
        sa.Column("normalized_value", sa.Text(), nullable=False),
        sa.Column("extraction_method", sa.String(80), nullable=False),
        sa.Column("extraction_version", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_facts_claim_id", "document_facts", ["claim_id"])
    op.create_index("ix_document_facts_document_id", "document_facts", ["document_id"])
    op.create_index("ix_document_facts_fact_type", "document_facts", ["fact_type"])
    op.create_index("ix_document_facts_tenant_id", "document_facts", ["tenant_id"])

    op.create_table(
        "fact_conflicts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("fact_type", sa.String(100), nullable=False),
        sa.Column("left_fact_id", sa.Uuid(), nullable=False),
        sa.Column("right_fact_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("detection_method", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
        sa.ForeignKeyConstraint(["left_fact_id"], ["document_facts.id"]),
        sa.ForeignKeyConstraint(["right_fact_id"], ["document_facts.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "claim_id", "fact_type", "left_fact_id", "right_fact_id", name="uq_fact_conflict"
        ),
    )
    op.create_index("ix_fact_conflicts_claim_id", "fact_conflicts", ["claim_id"])
    op.create_index("ix_fact_conflicts_tenant_id", "fact_conflicts", ["tenant_id"])

    op.create_table(
        "document_processing_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("detail", sa.String(500), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_processing_events_document_id", "document_processing_events", ["document_id"]
    )
    op.create_index(
        "ix_document_processing_events_correlation_id",
        "document_processing_events",
        ["correlation_id"],
    )
    op.create_index(
        "ix_document_processing_events_tenant_id", "document_processing_events", ["tenant_id"]
    )


def downgrade() -> None:
    op.drop_table("document_processing_events")
    op.drop_table("fact_conflicts")
    op.drop_table("document_facts")
    op.drop_table("document_pages")
    with op.batch_alter_table("documents") as batch:
        batch.drop_constraint("uq_document_hash", type_="unique")
        batch.drop_constraint("fk_documents_uploaded_by_user", type_="foreignkey")
        for column in [
            "updated_at",
            "error_detail",
            "error_code",
            "uploaded_by_user_id",
            "injection_risk",
            "classification_signals",
            "classification_version",
            "classification_method",
            "page_count",
            "extraction_status",
            "size_bytes",
            "checksum_sha256",
            "detected_mime_type",
            "extraction_artifact_key",
            "normalized_storage_key",
            "original_filename",
        ]:
            batch.drop_column(column)
