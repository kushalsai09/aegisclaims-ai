from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from insurance_platform.domain.entities import Actor
from insurance_platform.infrastructure.models import ClaimModel
from insurance_platform.infrastructure.repositories import ClaimRepository, DocumentRepository
from insurance_platform.retrieval.embeddings import DeterministicHashEmbeddingProvider
from insurance_platform.retrieval.generation import DeterministicGroundedGenerationProvider
from insurance_platform.retrieval.indexing import DocumentIndexingService
from insurance_platform.retrieval.search import (
    FUSION_VERSION,
    RetrievedEvidence,
    SqlHybridVectorIndex,
)


@dataclass(frozen=True, slots=True)
class RetrievalExecution:
    claim: ClaimModel
    evidence: list[RetrievedEvidence]
    duration_ms: float
    embedding_duration_ms: float
    candidate_count: int


@dataclass(frozen=True, slots=True)
class GroundedExecution:
    retrieval: RetrievalExecution
    state: str
    answer: str
    missing_information: list[str]
    ambiguity_indicators: list[str]
    human_review_required: bool
    provider: str
    model: str
    model_version: str
    generation_duration_ms: float


class RetrievalService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._claims = ClaimRepository(session)
        self._embedding = DeterministicHashEmbeddingProvider()
        self._index = SqlHybridVectorIndex(session)

    def retrieve(
        self, *, claim_id: UUID, actor: Actor, question: str, limit: int = 5
    ) -> RetrievalExecution:
        claim = self._claims.get_for_actor(claim_id, actor)
        if claim is None:
            raise LookupError("claim not found")
        started = time.perf_counter()
        DocumentIndexingService(self._session, self._embedding).index_claim(
            claim.id, actor.tenant_id
        )
        self._session.flush()
        embedding_started = time.perf_counter()
        query_vector = self._embedding.embed([question])[0]
        embedding_duration = (time.perf_counter() - embedding_started) * 1000
        evidence = self._index.search(
            tenant_id=actor.tenant_id,
            claim_id=claim.id,
            question=question,
            query_embedding=query_vector,
            applicable_policy_edition=claim.policy.edition,
            limit=limit,
        )
        duration = (time.perf_counter() - started) * 1000
        return RetrievalExecution(
            claim, evidence, duration, embedding_duration, self._index.candidate_count
        )


class GroundedAnswerService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._retrieval = RetrievalService(session)
        self._documents = DocumentRepository(session)
        self._generator = DeterministicGroundedGenerationProvider()

    def answer(
        self, *, claim_id: UUID, actor: Actor, question: str, limit: int = 5
    ) -> GroundedExecution:
        retrieval = self._retrieval.retrieve(
            claim_id=claim_id, actor=actor, question=question, limit=limit
        )
        text = "\n".join(item.chunk.normalized_text for item in retrieval.evidence)
        lower_question = question.lower()
        lower_text = text.lower()
        missing: list[str] = []
        ambiguity: list[str] = []
        if "estimate" in lower_question and "estimate amount" not in lower_text:
            missing.append("estimate")
        if "inspection" in lower_question and "inspection" not in lower_text:
            missing.append("inspection")
        causal_question = any(term in lower_question for term in ("cause", "caused", "why"))
        unsupported = causal_question and any(
            marker in lower_text
            for marker in ("no date, inspection", "cause allocation is unresolved")
        )
        if "cause allocation is unresolved" in lower_text:
            ambiguity.append("cause_allocation_unresolved")
        conflicts = self._documents.conflicts(claim_id, actor.tenant_id)
        conflict_relevant = bool(conflicts) and any(
            term in lower_question for term in ("date", "address", "policy", "reported")
        )
        if ambiguity:
            state = "ambiguous_evidence"
        elif not retrieval.evidence or missing or unsupported:
            state = "insufficient_evidence"
        elif conflict_relevant and not (
            "govern" in lower_question
            and all(conflict.fact_type == "policy_edition" for conflict in conflicts)
        ):
            state = "conflicting_evidence"
        else:
            state = "answerable"
        generation_started = time.perf_counter()
        answer = self._generator.generate(
            question=question,
            evidence=[item.chunk.normalized_text for item in retrieval.evidence],
            state=state,
        )
        generation_duration = (time.perf_counter() - generation_started) * 1000
        review_status = self._claims_review_status(claim_id, actor)
        return GroundedExecution(
            retrieval=retrieval,
            state=state,
            answer=answer,
            missing_information=missing,
            ambiguity_indicators=ambiguity,
            human_review_required=review_status not in {"not_required", "completed"},
            provider=self._generator.provider,
            model=self._generator.model,
            model_version=self._generator.version,
            generation_duration_ms=generation_duration,
        )

    def _claims_review_status(self, claim_id: UUID, actor: Actor) -> str:
        return ClaimRepository(self._session).review_status(claim_id, actor)


def stable_citation_id(chunk_identifier: str) -> str:
    return "CIT-" + hashlib.sha256(chunk_identifier.encode()).hexdigest()[:16].upper()


RETRIEVAL_CONFIGURATION = FUSION_VERSION
