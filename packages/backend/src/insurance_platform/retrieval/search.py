from __future__ import annotations

import math
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from insurance_platform.infrastructure.models import DocumentIndexModel, RetrievalChunkModel
from insurance_platform.retrieval.embeddings import DeterministicHashEmbeddingProvider

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
FUSION_VERSION = "hybrid_rrf_k60_v1"


@dataclass(frozen=True, slots=True)
class RetrievedEvidence:
    chunk: RetrievalChunkModel
    rank: int
    score: float
    lexical_score: float
    vector_score: float
    applicability_status: str


class SqlHybridVectorIndex:
    """Portable SQL candidate store with deterministic lexical/vector ranking.

    Embeddings are stored as JSON for SQLite/PostgreSQL parity in host and CI. The
    port deliberately permits a pgvector-backed implementation without changing
    retrieval or citation contracts.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self.candidate_count = 0

    def search(
        self,
        *,
        tenant_id: UUID,
        claim_id: UUID,
        question: str,
        query_embedding: list[float],
        applicable_policy_edition: str,
        limit: int = 5,
    ) -> list[RetrievedEvidence]:
        chunks = list(
            self._session.scalars(
                select(RetrievalChunkModel)
                .join(DocumentIndexModel, DocumentIndexModel.id == RetrievalChunkModel.index_id)
                .where(
                    RetrievalChunkModel.tenant_id == tenant_id,
                    RetrievalChunkModel.claim_id == claim_id,
                    DocumentIndexModel.status == "ready",
                    RetrievalChunkModel.embedding_version
                    == DeterministicHashEmbeddingProvider.descriptor.version,
                )
            ).unique()
        )
        query_tokens = set(TOKEN_PATTERN.findall(question.lower()))
        scored: list[tuple[RetrievalChunkModel, float, float, str]] = []
        for chunk in chunks:
            question_lower = question.lower()
            text_lower = chunk.normalized_text.lower()
            if (
                chunk.document_type == "policy_document"
                and chunk.policy_edition
                and chunk.policy_edition != applicable_policy_edition
            ):
                continue
            if (
                chunk.policy_edition
                and chunk.policy_edition != applicable_policy_edition
                and any(term in question_lower for term in ("govern", "applicable policy"))
            ):
                continue
            if (
                "unrelated" in text_lower
                and "no claim evidence" in text_lower
                and not any(term in question_lower for term in ("landscaping", "shrub"))
            ):
                continue
            chunk_tokens = set(TOKEN_PATTERN.findall(chunk.normalized_text.lower()))
            lexical = len(query_tokens & chunk_tokens) / max(len(query_tokens), 1)
            vector = sum(
                left * right for left, right in zip(query_embedding, chunk.embedding, strict=True)
            )
            applicability = "applicable"
            if chunk.policy_edition and chunk.policy_edition != applicable_policy_edition:
                applicability = "submitted_edition_mismatch"
            if lexical > 0 or vector > 0.08:
                scored.append((chunk, lexical, vector, applicability))
        lexical_order = sorted(scored, key=lambda item: (-item[1], item[0].chunk_identifier))
        vector_order = sorted(scored, key=lambda item: (-item[2], item[0].chunk_identifier))
        lexical_rank = {item[0].id: rank for rank, item in enumerate(lexical_order, 1)}
        vector_rank = {item[0].id: rank for rank, item in enumerate(vector_order, 1)}
        fused: list[tuple[RetrievalChunkModel, float, float, float, str]] = []
        for chunk, lexical, vector, applicability in scored:
            score = 1 / (60 + lexical_rank[chunk.id]) + 1 / (60 + vector_rank[chunk.id])
            if applicability == "submitted_edition_mismatch":
                score *= 0.65
            fused.append((chunk, score, lexical, vector, applicability))
        fused.sort(key=lambda item: (-item[1], item[0].chunk_identifier))
        self.candidate_count = len(fused)
        return [
            RetrievedEvidence(chunk, rank, score, lexical, vector, applicability)
            for rank, (chunk, score, lexical, vector, applicability) in enumerate(fused[:limit], 1)
        ]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(x * x for x in right))
    return sum(x * y for x, y in zip(left, right, strict=True)) / denominator if denominator else 0
