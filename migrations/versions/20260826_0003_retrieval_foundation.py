"""Add deterministic retrieval chunks and document index manifests.

Revision ID: 20260826_0003
Revises: 20260826_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0003"
down_revision: str | None = "20260826_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_indexes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("source_checksum", sa.String(64), nullable=False),
        sa.Column("chunker_version", sa.String(80), nullable=False),
        sa.Column("embedding_provider", sa.String(80), nullable=False),
        sa.Column("embedding_model", sa.String(120), nullable=False),
        sa.Column("embedding_version", sa.String(80), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "source_checksum",
            "chunker_version",
            "embedding_version",
            name="uq_document_index_version",
        ),
    )
    for column in ("tenant_id", "claim_id", "document_id"):
        op.create_index(f"ix_document_indexes_{column}", "document_indexes", [column])

    op.create_table(
        "retrieval_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("index_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("page_id", sa.Uuid(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("chunk_identifier", sa.String(80), nullable=False),
        sa.Column("chunk_ordinal", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(80), nullable=False),
        sa.Column("policy_edition", sa.String(80)),
        sa.Column("source_checksum", sa.String(64), nullable=False),
        sa.Column("page_checksum", sa.String(64), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("source_start", sa.Integer(), nullable=False),
        sa.Column("source_end", sa.Integer(), nullable=False),
        sa.Column("chunker_version", sa.String(80), nullable=False),
        sa.Column("embedding_provider", sa.String(80), nullable=False),
        sa.Column("embedding_model", sa.String(120), nullable=False),
        sa.Column("embedding_version", sa.String(80), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("injection_risk", sa.Boolean(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["index_id"], ["document_indexes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["page_id"], ["document_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_identifier", name="uq_retrieval_chunk_identifier"),
        sa.UniqueConstraint("index_id", "chunk_ordinal", name="uq_retrieval_index_ordinal"),
    )
    for column in (
        "index_id",
        "tenant_id",
        "claim_id",
        "document_id",
        "page_id",
        "chunk_identifier",
        "policy_edition",
    ):
        op.create_index(f"ix_retrieval_chunks_{column}", "retrieval_chunks", [column])


def downgrade() -> None:
    op.drop_table("retrieval_chunks")
    op.drop_table("document_indexes")
