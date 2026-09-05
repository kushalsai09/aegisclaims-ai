from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from insurance_platform.documents.classification import classify_document, detect_injection_risk
from insurance_platform.documents.extraction import DocumentExtractionError, extract_pages
from insurance_platform.documents.facts import extract_structured_facts
from insurance_platform.documents.ocr import OcrAdapter, UnavailableOcrAdapter
from insurance_platform.domain.entities import Actor
from insurance_platform.domain.enums import DocumentStatus
from insurance_platform.infrastructure.models import (
    AuditEventModel,
    DocumentFactModel,
    DocumentModel,
    DocumentPageModel,
    DocumentProcessingEventModel,
)
from insurance_platform.infrastructure.repositories import ClaimRepository, DocumentRepository
from insurance_platform.ports.object_storage import ObjectStorage
from insurance_platform.retrieval.indexing import DocumentIndexingService

MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf": "application/pdf", ".txt": "text/plain"}


class IngestionRejectedError(ValueError):
    def __init__(self, detail: str, code: str) -> None:
        super().__init__(detail)
        self.code = code


class DuplicateDocumentError(ValueError):
    def __init__(self, document_id: uuid.UUID) -> None:
        super().__init__("an identical document already exists for this claim")
        self.document_id = document_id


def safe_display_name(filename: str) -> str:
    leaf = Path(filename.replace("\\", "/")).name
    cleaned = re.sub(r"[^A-Za-z0-9._() -]", "_", leaf).strip(" .")
    return (cleaned or "uploaded-document")[:240]


def detect_mime(content: bytes) -> str:
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if b"\x00" not in content:
        try:
            content.decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            pass
    return "application/octet-stream"


def validate_upload(filename: str, declared_mime: str | None, content: bytes) -> tuple[str, str]:
    if not content:
        raise IngestionRejectedError("empty documents are not accepted", "document_empty")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise IngestionRejectedError("document exceeds the 5 MiB limit", "document_too_large")
    display_name = safe_display_name(filename)
    expected = ALLOWED_EXTENSIONS.get(Path(display_name).suffix.lower())
    if expected is None:
        raise IngestionRejectedError(
            "only text-native PDF and UTF-8 text files are allowed", "file_type_invalid"
        )
    detected = detect_mime(content)
    if detected != expected or declared_mime not in {expected, None, "application/octet-stream"}:
        raise IngestionRejectedError(
            "filename, declared MIME type, and detected content do not agree", "mime_mismatch"
        )
    return display_name, detected


class DocumentIngestionService:
    def __init__(
        self,
        session: Session,
        storage: ObjectStorage,
        *,
        ocr: OcrAdapter | None = None,
    ) -> None:
        self._session = session
        self._storage = storage
        self._ocr = ocr or UnavailableOcrAdapter()
        self._documents = DocumentRepository(session)
        self._claims = ClaimRepository(session)

    async def ingest(
        self,
        *,
        claim_id: uuid.UUID,
        actor: Actor,
        filename: str,
        declared_mime: str | None,
        content: bytes,
        correlation_id: str,
    ) -> DocumentModel:
        if self._claims.get_for_actor(claim_id, actor) is None:
            raise LookupError("claim not found")
        try:
            display_name, detected_mime = validate_upload(filename, declared_mime, content)
        except IngestionRejectedError as exc:
            self._audit(
                actor,
                "document.validation.failed",
                "claim",
                str(claim_id),
                correlation_id,
                {
                    "code": exc.code,
                    "filename": safe_display_name(filename),
                    "size_bytes": len(content),
                },
                outcome="rejected",
            )
            self._session.commit()
            raise
        checksum = hashlib.sha256(content).hexdigest()
        duplicate = self._documents.duplicate(actor.tenant_id, claim_id, checksum)
        if duplicate is not None:
            self._audit(
                actor,
                "document.upload.duplicate",
                "document",
                str(duplicate.id),
                correlation_id,
                {"checksum_sha256": checksum},
                outcome="rejected",
            )
            self._session.commit()
            raise DuplicateDocumentError(duplicate.id)
        document_id = uuid.uuid4()
        suffix = Path(display_name).suffix.lower()
        base_key = f"{actor.tenant_id}/{claim_id}/{document_id}"
        document = DocumentModel(
            id=document_id,
            tenant_id=actor.tenant_id,
            claim_id=claim_id,
            name=display_name,
            original_filename=display_name,
            document_type="unclassified",
            storage_key=f"{base_key}/original/{checksum}{suffix}",
            normalized_storage_key=f"{base_key}/derived/normalized.txt",
            extraction_artifact_key=f"{base_key}/derived/extraction.json",
            content_type=detected_mime,
            detected_mime_type=detected_mime,
            checksum_sha256=checksum,
            size_bytes=len(content),
            processing_status=DocumentStatus.UPLOADED,
            extraction_status="pending",
            uploaded_by_user_id=actor.user_id,
            synthetic_label="SYNTHETIC DEMONSTRATION DATA",
            updated_at=datetime.now(UTC),
        )
        self._session.add(document)
        self._transition(
            document, actor, DocumentStatus.UPLOADED, "Upload accepted", correlation_id
        )
        self._session.commit()
        return await self.process(document.id, actor, content, correlation_id)

    async def process(
        self,
        document_id: uuid.UUID,
        actor: Actor,
        content: bytes | None,
        correlation_id: str,
    ) -> DocumentModel:
        document = self._documents.get_for_actor(document_id, actor)
        if document is None:
            raise LookupError("document not found")
        if document.processing_status == DocumentStatus.READY:
            return document
        if content is None:
            content = await self._storage.get_bytes(document.storage_key)
        try:
            self._transition(
                document,
                actor,
                DocumentStatus.VALIDATING,
                "Integrity metadata verified",
                correlation_id,
            )
            self._session.commit()
            await self._storage.put_bytes(
                document.storage_key, content, document.detected_mime_type
            )
            self._transition(
                document, actor, DocumentStatus.STORED, "Immutable original stored", correlation_id
            )
            self._session.commit()
            self._transition(
                document,
                actor,
                DocumentStatus.EXTRACTING,
                "Text extraction started",
                correlation_id,
            )
            self._session.commit()
            pages, extraction_method = await extract_pages(
                content, document.detected_mime_type, self._ocr
            )
            self._session.execute(
                delete(DocumentPageModel).where(DocumentPageModel.document_id == document.id)
            )
            self._session.execute(
                delete(DocumentFactModel).where(DocumentFactModel.document_id == document.id)
            )
            for number, text in enumerate(pages, start=1):
                self._session.add(
                    DocumentPageModel(
                        tenant_id=document.tenant_id,
                        document_id=document.id,
                        page_number=number,
                        text=text,
                        text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                        extraction_method=extraction_method,
                        extraction_version="1",
                    )
                )
            document.page_count = len(pages)
            document.extraction_status = "extracted"
            self._transition(
                document,
                actor,
                DocumentStatus.CLASSIFYING,
                "Deterministic classification started",
                correlation_id,
            )
            self._session.commit()
            classification = classify_document(document.name, pages)
            document.document_type = classification.document_type
            document.classification_method = classification.method
            document.classification_version = classification.version
            document.classification_signals = classification.signals
            document.injection_risk = detect_injection_risk(pages)
            self._transition(
                document,
                actor,
                DocumentStatus.NORMALIZING,
                "Structured facts and provenance created",
                correlation_id,
            )
            self._session.commit()
            facts = extract_structured_facts(pages)
            for fact in facts:
                self._session.add(
                    DocumentFactModel(
                        tenant_id=document.tenant_id,
                        claim_id=document.claim_id,
                        document_id=document.id,
                        page_number=fact.page_number,
                        fact_type=fact.fact_type,
                        raw_source_span=fact.raw_source_span,
                        normalized_value=fact.normalized_value,
                        extraction_method="deterministic_regex",
                        extraction_version="1",
                    )
                )
            normalized = "\n\n".join(f"--- Page {i} ---\n{text}" for i, text in enumerate(pages, 1))
            artifact = json.dumps(
                {"document_id": str(document.id), "method": extraction_method, "pages": pages},
                sort_keys=True,
            ).encode()
            assert document.normalized_storage_key is not None
            assert document.extraction_artifact_key is not None
            await self._storage.put_bytes(
                document.normalized_storage_key, normalized.encode(), "text/plain"
            )
            await self._storage.put_bytes(
                document.extraction_artifact_key, artifact, "application/json"
            )
            self._session.flush()
            self._documents.rebuild_conflicts(document.claim_id, document.tenant_id)
            self._session.expire(document, ["pages", "facts"])
            DocumentIndexingService(self._session).index_document(document.id)
            document.error_code = None
            document.error_detail = None
            self._transition(
                document,
                actor,
                DocumentStatus.READY,
                "Document processing completed",
                correlation_id,
            )
            self._session.commit()
            return document
        except Exception as exc:
            self._session.rollback()
            document = self._documents.get_for_actor(document_id, actor)
            assert document is not None
            document.processing_status = DocumentStatus.FAILED
            document.extraction_status = "failed"
            document.error_code = (
                "extraction_failed"
                if isinstance(exc, DocumentExtractionError)
                else "processing_failed"
            )
            document.error_detail = str(exc)[:500]
            self._transition(
                document,
                actor,
                DocumentStatus.FAILED,
                document.error_detail,
                correlation_id,
                outcome="failure",
            )
            self._session.commit()
            return document

    def _transition(
        self,
        document: DocumentModel,
        actor: Actor,
        status: DocumentStatus,
        detail: str,
        correlation_id: str,
        *,
        outcome: str = "success",
    ) -> None:
        document.processing_status = status
        document.updated_at = datetime.now(UTC)
        self._session.add(
            DocumentProcessingEventModel(
                tenant_id=document.tenant_id,
                document_id=document.id,
                status=status,
                detail=detail,
                correlation_id=correlation_id,
            )
        )
        self._audit(
            actor,
            f"document.{status.value}",
            "document",
            str(document.id),
            correlation_id,
            {"status": status.value, "document_type": document.document_type},
            outcome=outcome,
        )
        self._session.flush()

    def _audit(
        self,
        actor: Actor,
        action: str,
        resource_type: str,
        resource_id: str,
        correlation_id: str,
        details: dict[str, object],
        *,
        outcome: str = "success",
    ) -> None:
        self._session.add(
            AuditEventModel(
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                outcome=outcome,
                correlation_id=correlation_id,
                details=details,
            )
        )
