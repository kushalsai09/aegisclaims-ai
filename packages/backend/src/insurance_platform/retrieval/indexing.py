from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from insurance_platform.infrastructure.models import (
    DocumentIndexModel,
    DocumentModel,
    DocumentPageModel,
    RetrievalChunkModel,
)
from insurance_platform.retrieval.chunking import CHUNKER_VERSION, DeterministicChunk, chunk_page
from insurance_platform.retrieval.embeddings import DeterministicHashEmbeddingProvider


class DocumentIndexingService:
    def __init__(self, session: Session, embedding_provider=None) -> None:  # type: ignore[no-untyped-def]
        self._session = session
        self._embedding = embedding_provider or DeterministicHashEmbeddingProvider()

    def index_document(self, document_id: uuid.UUID) -> DocumentIndexModel:
        document = self._session.get(DocumentModel, document_id)
        if document is None:
            raise LookupError("document not found")
        descriptor = self._embedding.descriptor
        existing = self._session.scalar(
            select(DocumentIndexModel).where(
                DocumentIndexModel.document_id == document.id,
                DocumentIndexModel.source_checksum == document.checksum_sha256,
                DocumentIndexModel.chunker_version == CHUNKER_VERSION,
                DocumentIndexModel.embedding_version == descriptor.version,
            )
        )
        if existing is not None and existing.status == "ready":
            return existing
        index = existing or DocumentIndexModel(
            tenant_id=document.tenant_id,
            claim_id=document.claim_id,
            document_id=document.id,
            source_checksum=document.checksum_sha256,
            chunker_version=CHUNKER_VERSION,
            embedding_provider=descriptor.provider,
            embedding_model=descriptor.model,
            embedding_version=descriptor.version,
            embedding_dimensions=descriptor.dimensions,
            status="indexing",
        )
        self._session.add(index)
        self._session.flush()
        self._session.execute(
            delete(RetrievalChunkModel).where(RetrievalChunkModel.index_id == index.id)
        )
        policy_editions = {
            fact.normalized_value for fact in document.facts if fact.fact_type == "policy_edition"
        }
        policy_edition = sorted(policy_editions)[0] if policy_editions else None
        pending: list[tuple[DocumentPageModel, DeterministicChunk]] = []
        for page in sorted(document.pages, key=lambda item: item.page_number):
            for chunk in chunk_page(document.id, page.text_sha256, page.text):
                pending.append((page, chunk))
        try:
            vectors = self._embedding.embed([chunk.text for _, chunk in pending])
        except Exception as exc:
            index.status = "failed"
            index.error_code = type(exc).__name__[:100]
            index.completed_at = datetime.now(UTC)
            self._session.flush()
            raise
        for (page, chunk), vector in zip(pending, vectors, strict=True):
            self._session.add(
                RetrievalChunkModel(
                    index_id=index.id,
                    tenant_id=document.tenant_id,
                    claim_id=document.claim_id,
                    document_id=document.id,
                    page_id=page.id,
                    page_number=page.page_number,
                    chunk_identifier=chunk.identifier,
                    chunk_ordinal=chunk.ordinal,
                    document_type=document.document_type,
                    policy_edition=policy_edition,
                    source_checksum=document.checksum_sha256,
                    page_checksum=page.text_sha256,
                    normalized_text=chunk.text,
                    source_start=chunk.source_start,
                    source_end=chunk.source_end,
                    chunker_version=CHUNKER_VERSION,
                    embedding_provider=descriptor.provider,
                    embedding_model=descriptor.model,
                    embedding_version=descriptor.version,
                    embedding=vector,
                    injection_risk=document.injection_risk,
                )
            )
        index.status = "ready"
        index.chunk_count = len(pending)
        index.error_code = None
        index.completed_at = datetime.now(UTC)
        self._session.flush()
        return index

    def index_claim(self, claim_id: uuid.UUID, tenant_id: uuid.UUID) -> int:
        documents = list(
            self._session.scalars(
                select(DocumentModel).where(
                    DocumentModel.claim_id == claim_id,
                    DocumentModel.tenant_id == tenant_id,
                    DocumentModel.processing_status == "ready",
                )
            )
        )
        for document in documents:
            self.index_document(document.id)
        return len(documents)
