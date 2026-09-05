from __future__ import annotations

import hashlib
import json
from typing import Literal
from uuid import UUID

from opentelemetry import trace
from prometheus_client import Counter, Histogram
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from insurance_platform.application.schemas import CitationView, ClaimEvidenceBriefView
from insurance_platform.domain.entities import Actor
from insurance_platform.infrastructure.models import (
    AuditEventModel,
    ClaimEvidenceBriefModel,
    ModelInvocationModel,
    WorkflowRunModel,
)
from insurance_platform.infrastructure.repositories import ClaimRepository
from insurance_platform.ports.model_provider import (
    ModelEvidence,
    ModelProvider,
    ModelProviderError,
    ModelProviderThrottled,
    ModelProviderTimeout,
    StructuredGenerationRequest,
)
from insurance_platform.retrieval.search import FUSION_VERSION, RetrievedEvidence
from insurance_platform.retrieval.service import RetrievalService, stable_citation_id

PROMPT_TEMPLATE_VERSION = "claim_evidence_brief_prompt_v1"
BRIEF_SCHEMA_VERSION = "claim_evidence_brief_schema_v1"
PROHIBITED_PHRASES = (
    "approve this claim",
    "deny this claim",
    "issue payment",
    "settlement recommendation",
    "fraudulent claim",
    "liable for",
    "send to the claimant",
    "close this claim",
)
tracer = trace.get_tracer("insurance_platform.model_assistance")
MODEL_INVOCATIONS = Counter(
    "insurance_model_invocations_total", "Governed model invocations", ["outcome"]
)
MODEL_VALIDATION_FAILURES = Counter(
    "insurance_model_validation_failures_total", "Rejected model outputs", ["reason"]
)
MODEL_LATENCY = Histogram(
    "insurance_model_invocation_latency_seconds", "Governed model invocation latency"
)
MODEL_HUMAN_REVIEW = Counter(
    "insurance_model_human_review_routes_total", "Briefs routed to human review"
)
MODEL_PROVIDER_EVENTS = Counter(
    "insurance_model_provider_events_total",
    "Governed provider events",
    ["event"],
)
MODEL_TOKEN_USAGE = Counter(
    "insurance_model_token_usage_total",
    "Provider-reported token usage",
    ["provider", "direction"],
)
MODEL_PROVIDER_TOKEN_USAGE = Counter(
    "insurance_model_provider_tokens_total",
    "Provider-reported billing token usage; deterministic estimates are excluded",
    ["provider", "model", "direction"],
)
MODEL_PROVIDER_LATENCY = Histogram(
    "insurance_model_provider_latency_seconds",
    "Provider-reported model latency",
    ["provider", "model", "outcome"],
)
MODEL_PROVIDER_RETRIES = Counter(
    "insurance_model_provider_retries_total",
    "Bounded application-level model retries",
    ["provider", "model"],
)


class BriefCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    status: Literal[
        "supported", "insufficient_evidence", "conflicting_evidence", "ambiguous_evidence"
    ]
    claim_summary: str = Field(min_length=1, max_length=1200)
    evidence_summary: str = Field(min_length=1, max_length=2000)
    applicable_policy_summary: str = Field(min_length=1, max_length=1200)
    missing_information: list[str] = Field(max_length=20)
    conflicts: list[str] = Field(max_length=20)
    ambiguities: list[str] = Field(max_length=20)
    safety_flags: list[str] = Field(max_length=20)
    citation_handles: list[str] = Field(max_length=10)
    human_review_required: bool
    limitations: list[str] = Field(min_length=1, max_length=20)


class BriefNotFoundError(Exception):
    pass


class BriefConflictError(Exception):
    pass


class BriefGenerationError(Exception):
    pass


class ClaimEvidenceBriefService:
    def __init__(
        self,
        session: Session,
        provider: ModelProvider,
        *,
        timeout_seconds: float = 8.0,
        max_retries: int = 1,
        max_input_characters: int = 30_000,
        max_output_tokens: int = 1_200,
    ) -> None:
        self._session = session
        self._provider = provider
        self._claims = ClaimRepository(session)
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._max_input_characters = max_input_characters
        self._max_output_tokens = max_output_tokens

    def create(
        self,
        *,
        claim_id: UUID,
        actor: Actor,
        task: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> ClaimEvidenceBriefView:
        claim = self._claims.get_for_actor(claim_id, actor)
        if claim is None:
            raise BriefNotFoundError("claim not found")
        existing = self._session.scalar(
            select(ClaimEvidenceBriefModel).where(
                ClaimEvidenceBriefModel.tenant_id == actor.tenant_id,
                ClaimEvidenceBriefModel.claim_id == claim_id,
                ClaimEvidenceBriefModel.idempotency_key == idempotency_key,
            )
        )
        if existing:
            if existing.task != task:
                raise BriefConflictError("idempotency key was already used for another task")
            return self.view(existing, actor)

        with tracer.start_as_current_span("claim_brief.retrieve"):
            retrieval = RetrievalService(self._session).retrieve(
                claim_id=claim_id, actor=actor, question=task, limit=5
            )
        citations = {
            stable_citation_id(item.chunk.chunk_identifier): item for item in retrieval.evidence
        }
        fingerprint = self._fingerprint(claim_id, actor, task)
        workflow = self._session.scalar(
            select(WorkflowRunModel)
            .where(
                WorkflowRunModel.tenant_id == actor.tenant_id,
                WorkflowRunModel.claim_id == claim_id,
            )
            .order_by(WorkflowRunModel.created_at.desc())
            .limit(1)
        )
        remaining = self._max_input_characters
        bounded_evidence: list[ModelEvidence] = []
        for handle, item in citations.items():
            if remaining <= 0:
                break
            text = item.chunk.normalized_text[:remaining]
            bounded_evidence.append(
                ModelEvidence(
                    handle=handle,
                    text=text,
                    policy_edition=item.chunk.policy_edition,
                    injection_risk=item.chunk.injection_risk,
                )
            )
            remaining -= len(text)
        request = StructuredGenerationRequest(
            task=task,
            claim_number=claim.claim_number,
            applicable_policy_edition=claim.policy.edition,
            evidence=bounded_evidence,
            correlation_id=correlation_id,
            prompt_template_version=PROMPT_TEMPLATE_VERSION,
            response_schema_version=BRIEF_SCHEMA_VERSION,
            response_schema=BriefCandidate.model_json_schema(),
            max_output_tokens=self._max_output_tokens,
        )
        prompt_hash = hashlib.sha256(
            json.dumps(
                {
                    "task": task,
                    "claim": claim.claim_number,
                    "policy": claim.policy.edition,
                    "handles": sorted(citations),
                    "template": PROMPT_TEMPLATE_VERSION,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        failures: list[str] = []
        result = None
        candidate = None
        attempts_used = 0
        for attempt in range(self._max_retries + 1):
            attempts_used = attempt + 1
            try:
                with tracer.start_as_current_span("claim_brief.model.invoke"):
                    result = self._provider.generate_structured(
                        request, timeout_seconds=self._timeout_seconds
                    )
                with tracer.start_as_current_span("claim_brief.validate"):
                    candidate = BriefCandidate.model_validate_json(result.content)
                    failures = self._validate(candidate, citations, claim.policy.edition)
                if not failures:
                    break
            except ValidationError:
                failures = ["malformed_structured_output"]
            except ModelProviderTimeout:
                MODEL_PROVIDER_EVENTS.labels(event="timeout").inc()
                failures = ["provider_timeout"]
            except ModelProviderThrottled:
                MODEL_PROVIDER_EVENTS.labels(event="throttled").inc()
                failures = ["provider_throttled"]
            except ModelProviderError:
                MODEL_PROVIDER_EVENTS.labels(event="failure").inc()
                failures = ["provider_unavailable"]
            if attempt < self._max_retries:
                MODEL_PROVIDER_EVENTS.labels(event="retry").inc()
        invocation = ModelInvocationModel(
            tenant_id=actor.tenant_id,
            claim_id=claim_id,
            workflow_run_id=workflow.id if workflow else None,
            actor_user_id=actor.user_id,
            provider=self._provider.provider_id,
            model_identifier=self._provider.model_id,
            configuration_version=self._provider.configuration_version,
            prompt_template_version=PROMPT_TEMPLATE_VERSION,
            retrieval_configuration=FUSION_VERSION,
            response_schema_version=BRIEF_SCHEMA_VERSION,
            evidence_fingerprint=fingerprint,
            authorized_citation_ids=sorted(citations),
            prompt_hash=prompt_hash,
            outcome="valid" if candidate is not None and not failures else "rejected",
            validation_failures=failures,
            latency_ms=result.latency_ms if result else None,
            input_tokens=result.input_tokens if result else None,
            output_tokens=result.output_tokens if result else None,
            retry_count=max(attempts_used - 1, 0),
            correlation_id=correlation_id,
        )
        self._session.add(invocation)
        self._session.flush()
        if invocation.retry_count:
            MODEL_PROVIDER_RETRIES.labels(
                provider=self._provider.provider_id, model=self._provider.model_id
            ).inc(invocation.retry_count)
        if result:
            MODEL_PROVIDER_LATENCY.labels(
                provider=self._provider.provider_id,
                model=self._provider.model_id,
                outcome=invocation.outcome,
            ).observe(result.latency_ms / 1000)
        if candidate is None or failures:
            MODEL_INVOCATIONS.labels(outcome="rejected").inc()
            for failure in failures:
                MODEL_VALIDATION_FAILURES.labels(reason=failure).inc()
            self._audit(invocation, actor, "model.brief.rejected")
            self._session.commit()
            raise BriefGenerationError("model-assisted brief could not pass safety validation")

        human_review = candidate.human_review_required or self._claims.review_status(
            claim_id, actor
        ) not in {"not_required", "completed"}
        MODEL_INVOCATIONS.labels(outcome="valid").inc()
        if result:
            MODEL_LATENCY.observe(result.latency_ms / 1000)
            if result.input_tokens is not None:
                MODEL_TOKEN_USAGE.labels(
                    provider=self._provider.provider_id, direction="input"
                ).inc(result.input_tokens)
                if self._provider.provider_id != "local_deterministic":
                    MODEL_PROVIDER_TOKEN_USAGE.labels(
                        provider=self._provider.provider_id,
                        model=self._provider.model_id,
                        direction="input",
                    ).inc(result.input_tokens)
            if result.output_tokens is not None:
                MODEL_TOKEN_USAGE.labels(
                    provider=self._provider.provider_id, direction="output"
                ).inc(result.output_tokens)
                if self._provider.provider_id != "local_deterministic":
                    MODEL_PROVIDER_TOKEN_USAGE.labels(
                        provider=self._provider.provider_id,
                        model=self._provider.model_id,
                        direction="output",
                    ).inc(result.output_tokens)
        if human_review:
            MODEL_HUMAN_REVIEW.inc()
        content = candidate.model_dump(exclude={"citation_handles", "status"})
        content["human_review_required"] = human_review
        content["citations"] = [
            self._citation(citations[handle], claim_id).model_dump(mode="json")
            for handle in candidate.citation_handles
        ]
        content["authority_notice"] = (
            "AI-assisted evidence brief. Decision remains with the authorized reviewer."
        )
        brief = ClaimEvidenceBriefModel(
            tenant_id=actor.tenant_id,
            claim_id=claim_id,
            workflow_run_id=workflow.id if workflow else None,
            invocation_id=invocation.id,
            created_by_user_id=actor.user_id,
            task=task,
            status=candidate.status,
            content=content,
            evidence_fingerprint=fingerprint,
            applicable_policy_edition=claim.policy.edition,
            idempotency_key=idempotency_key,
            validation_state="valid",
        )
        self._session.add(brief)
        self._audit(invocation, actor, "model.brief.created")
        self._session.commit()
        return self.view(brief, actor)

    def get(self, brief_id: UUID, actor: Actor) -> ClaimEvidenceBriefModel:
        brief = self._session.scalar(
            select(ClaimEvidenceBriefModel).where(
                ClaimEvidenceBriefModel.id == brief_id,
                ClaimEvidenceBriefModel.tenant_id == actor.tenant_id,
            )
        )
        if brief is None or self._claims.get_for_actor(brief.claim_id, actor) is None:
            raise BriefNotFoundError("brief not found")
        return brief

    def latest(self, claim_id: UUID, actor: Actor) -> ClaimEvidenceBriefView | None:
        if self._claims.get_for_actor(claim_id, actor) is None:
            raise BriefNotFoundError("claim not found")
        brief = self._session.scalar(
            select(ClaimEvidenceBriefModel)
            .where(
                ClaimEvidenceBriefModel.claim_id == claim_id,
                ClaimEvidenceBriefModel.tenant_id == actor.tenant_id,
            )
            .order_by(ClaimEvidenceBriefModel.created_at.desc())
            .limit(1)
        )
        return self.view(brief, actor) if brief else None

    def view(self, brief: ClaimEvidenceBriefModel, actor: Actor) -> ClaimEvidenceBriefView:
        invocation = self._session.get(ModelInvocationModel, brief.invocation_id)
        assert invocation is not None
        stale = brief.evidence_fingerprint != self._fingerprint(brief.claim_id, actor, brief.task)
        return ClaimEvidenceBriefView(
            id=brief.id,
            claim_id=brief.claim_id,
            workflow_id=brief.workflow_run_id,
            task=brief.task,
            status=brief.status,
            stale=stale,
            validation_state="stale" if stale else brief.validation_state,
            evidence_fingerprint=brief.evidence_fingerprint,
            applicable_policy_edition=brief.applicable_policy_edition,
            provider=invocation.provider,
            model_identifier=invocation.model_identifier,
            configuration_version=invocation.configuration_version,
            prompt_template_version=invocation.prompt_template_version,
            retrieval_configuration=invocation.retrieval_configuration,
            response_schema_version=invocation.response_schema_version,
            latency_ms=invocation.latency_ms,
            input_tokens=invocation.input_tokens,
            output_tokens=invocation.output_tokens,
            retry_count=invocation.retry_count,
            correlation_id=invocation.correlation_id,
            created_at=brief.created_at,
            **brief.content,
        )

    @staticmethod
    def _validate(
        candidate: BriefCandidate,
        citations: dict[str, RetrievedEvidence],
        policy_edition: str,
    ) -> list[str]:
        failures: list[str] = []
        if any(handle not in citations for handle in candidate.citation_handles):
            failures.append("unauthorized_citation")
        if any(
            citations[handle].chunk.policy_edition not in {None, policy_edition}
            for handle in candidate.citation_handles
            if handle in citations
        ):
            failures.append("wrong_policy_citation")
        text = " ".join(
            [candidate.claim_summary, candidate.evidence_summary, *candidate.limitations]
        ).lower()
        if any(phrase in text for phrase in PROHIBITED_PHRASES):
            failures.append("prohibited_consequential_output")
        return failures

    def _fingerprint(self, claim_id: UUID, actor: Actor, task: str) -> str:
        documents = self._claims.documents(claim_id, actor)
        material = "|".join(sorted(item.checksum_sha256 for item in documents)) + "|" + task
        return hashlib.sha256(material.encode()).hexdigest()

    @staticmethod
    def _citation(item: RetrievedEvidence, claim_id: UUID) -> CitationView:
        chunk = item.chunk
        return CitationView(
            id=stable_citation_id(chunk.chunk_identifier),
            claim_id=claim_id,
            document_id=chunk.document_id,
            document_name=chunk.document.name,
            document_type=chunk.document_type,
            page_number=chunk.page_number,
            chunk_identifier=chunk.chunk_identifier,
            chunk_ordinal=chunk.chunk_ordinal,
            source_start=chunk.source_start,
            source_end=chunk.source_end,
            source_checksum=chunk.source_checksum,
            page_checksum=chunk.page_checksum,
            excerpt=chunk.normalized_text,
            policy_edition=chunk.policy_edition,
            applicability_status=item.applicability_status,
            injection_risk=chunk.injection_risk,
            retrieval_rank=item.rank,
            retrieval_score=round(item.score, 8),
            lexical_score=round(item.lexical_score, 8),
            vector_score=round(item.vector_score, 8),
            retrieval_method=FUSION_VERSION,
            source_url=f"/documents/{chunk.document_id}?page={chunk.page_number}#page-{chunk.page_number}",
        )

    def _audit(self, invocation: ModelInvocationModel, actor: Actor, action: str) -> None:
        self._session.add(
            AuditEventModel(
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                action=action,
                resource_type="model_invocation",
                resource_id=str(invocation.id),
                outcome=invocation.outcome,
                correlation_id=invocation.correlation_id,
                details={
                    "provider": invocation.provider,
                    "model": invocation.model_identifier,
                    "prompt_hash": invocation.prompt_hash,
                    "validation_failures": invocation.validation_failures,
                    "retry_count": invocation.retry_count,
                },
            )
        )
