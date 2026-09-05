from __future__ import annotations

from collections.abc import Iterator
from typing import cast

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from insurance_platform.domain.entities import Actor
from insurance_platform.infrastructure.repositories import DocumentRepository
from insurance_platform.retrieval.search import FUSION_VERSION, RetrievedEvidence
from insurance_platform.retrieval.service import GroundedAnswerService, stable_citation_id
from insurance_platform.workflows.state import FORBIDDEN_ACTIONS, WorkflowState


def citation_dict(item: RetrievedEvidence, claim_id: str) -> dict[str, object]:
    chunk = item.chunk
    return {
        "id": stable_citation_id(chunk.chunk_identifier),
        "claim_id": claim_id,
        "document_id": str(chunk.document_id),
        "document_name": chunk.document.name,
        "document_type": chunk.document_type,
        "page_number": chunk.page_number,
        "chunk_identifier": chunk.chunk_identifier,
        "chunk_ordinal": chunk.chunk_ordinal,
        "source_start": chunk.source_start,
        "source_end": chunk.source_end,
        "source_checksum": chunk.source_checksum,
        "page_checksum": chunk.page_checksum,
        "excerpt": chunk.normalized_text,
        "policy_edition": chunk.policy_edition,
        "applicability_status": item.applicability_status,
        "injection_risk": chunk.injection_risk,
        "retrieval_rank": item.rank,
        "retrieval_score": round(item.score, 8),
        "lexical_score": round(item.lexical_score, 8),
        "vector_score": round(item.vector_score, 8),
        "retrieval_method": FUSION_VERSION,
        "source_url": (
            f"/documents/{chunk.document_id}?page={chunk.page_number}#page-{chunk.page_number}"
        ),
    }


class ControlledWorkflowGraph:
    """Narrow LangGraph router; persistence and authorization stay in the application layer."""

    def __init__(self, session: Session, actor: Actor) -> None:
        self._session = session
        self._actor = actor
        graph = StateGraph(WorkflowState)
        graph.add_node("load_claim_context", self._load_claim_context)
        graph.add_node("retrieve_evidence", self._retrieve_evidence)
        graph.add_node("validate_provenance", self._validate_provenance)
        graph.add_node("determine_review", self._determine_review)
        graph.add_node("prepare_artifact", self._prepare_artifact)
        graph.add_edge(START, "load_claim_context")
        graph.add_edge("load_claim_context", "retrieve_evidence")
        graph.add_edge("retrieve_evidence", "validate_provenance")
        graph.add_edge("validate_provenance", "determine_review")
        graph.add_edge("determine_review", "prepare_artifact")
        graph.add_edge("prepare_artifact", END)
        self._graph = graph.compile()

    def stream(self, state: WorkflowState) -> Iterator[WorkflowState]:
        for value in self._graph.stream(state, stream_mode="values"):
            yield cast(WorkflowState, value)

    def _load_claim_context(self, state: WorkflowState) -> dict[str, object]:
        return {"current_stage": "gathering_evidence", "status": "gathering_evidence"}

    def _retrieve_evidence(self, state: WorkflowState) -> dict[str, object]:
        result = GroundedAnswerService(self._session).answer(
            claim_id=self._uuid(state["claim_id"]),
            actor=self._actor,
            question=state["task"],
            limit=5,
        )
        citations = [citation_dict(item, state["claim_id"]) for item in result.retrieval.evidence]
        missing = list(result.missing_information)
        if result.state == "insufficient_evidence" and not missing:
            missing.append("answer_support")
        conflicts = [
            {
                "fact_type": item.fact_type,
                "left_document_name": item.left_fact.document.name,
                "left_value": item.left_fact.normalized_value,
                "right_document_name": item.right_fact.document.name,
                "right_value": item.right_fact.normalized_value,
            }
            for item in DocumentRepository(self._session).conflicts(
                self._uuid(state["claim_id"]), self._actor.tenant_id
            )
        ]
        return {
            "current_stage": "evaluating_evidence",
            "status": result.state,
            "retrieved_evidence": citations,
            "citations": citations,
            "conflicts": conflicts,
            "ambiguities": result.ambiguity_indicators,
            "missing_information": missing,
            "prompt_injection_indicators": [
                "untrusted_document_instructions_present"
                for item in citations
                if item["injection_risk"]
            ],
        }

    def _validate_provenance(self, state: WorkflowState) -> dict[str, object]:
        invalid = [item for item in state["citations"] if item["claim_id"] != state["claim_id"]]
        if invalid:
            return {
                "current_stage": "provenance_validation_failed",
                "status": "failed",
                "error_code": "citation_scope_invalid",
                "error_detail": "Citation provenance did not match the authorized claim.",
            }
        return {"current_stage": "determining_review_requirements"}

    def _determine_review(self, state: WorkflowState) -> dict[str, object]:
        if state["status"] == "failed":
            return {}
        reasons: list[str] = []
        if state["status"] == "insufficient_evidence":
            reasons.append("insufficient_evidence")
        if state["missing_information"]:
            reasons.append("required_evidence_missing")
        if state["conflicts"] and state["status"] == "conflicting_evidence":
            reasons.append("material_evidence_conflict")
        if state["ambiguities"]:
            reasons.append("material_ambiguity")
        if state["prompt_injection_indicators"]:
            reasons.append("untrusted_content_detected")
        if state["human_review_required"]:
            reasons.append("synthetic_scenario_mandates_review")
        requires_review = bool(reasons)
        return {
            "human_review_required": requires_review,
            "human_review_reason": ",".join(dict.fromkeys(reasons)) or None,
            "approval_state": "pending" if requires_review else "not_required",
        }

    def _prepare_artifact(self, state: WorkflowState) -> dict[str, object]:
        if state["status"] == "failed":
            return {"current_stage": "failed"}
        proposals: list[str]
        if state["missing_information"]:
            proposals = [f"Request missing {item}." for item in state["missing_information"]]
        elif state["conflicts"]:
            proposals = ["Inspect each conflicting source; do not select a value automatically."]
        elif state["ambiguities"]:
            proposals = ["Route the cited policy language to an authorized human reviewer."]
        elif state["prompt_injection_indicators"]:
            proposals = ["Review the flagged document as untrusted evidence only."]
        elif state["human_review_required"]:
            proposals = ["Complete the mandatory supervisor evidence review."]
        else:
            proposals = ["Record that the cited evidence bundle is ready for human use."]
        awaiting = state["human_review_required"]
        return {
            "current_stage": "awaiting_human_review" if awaiting else "completed",
            "status": "awaiting_human_review" if awaiting else "completed",
            "proposed_next_steps": proposals,
        }

    @staticmethod
    def artifact(state: WorkflowState) -> dict[str, object]:
        citations = state["citations"]
        return {
            "established_evidence": [
                {"citation_id": item["id"], "document_name": item["document_name"]}
                for item in citations
            ],
            "applicable_policy_evidence": [
                {"citation_id": item["id"], "policy_edition": item["policy_edition"]}
                for item in citations
                if item["policy_edition"] == state["applicable_policy_edition"]
            ],
            "conflicting_evidence": state["conflicts"],
            "ambiguous_evidence": state["ambiguities"],
            "missing_information": state["missing_information"],
            "untrusted_content_flags": state["prompt_injection_indicators"],
            "proposed_next_steps": state["proposed_next_steps"],
            "human_review_reason": state["human_review_reason"],
            "citations": citations,
            "authority_notice": (
                "SYSTEM-GENERATED PROPOSAL — evidence support only. An authorized human remains "
                "the decision authority; no claim decision or external action was performed."
            ),
            "forbidden_actions": FORBIDDEN_ACTIONS,
        }

    @staticmethod
    def _uuid(value: str):  # type: ignore[no-untyped-def]
        from uuid import UUID

        return UUID(value)
