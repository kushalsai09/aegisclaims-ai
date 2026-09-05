from __future__ import annotations

import json
import time

from insurance_platform.ports.model_provider import (
    ModelGenerationResult,
    ModelProviderError,
    ModelProviderTimeout,
    StructuredGenerationRequest,
)


class DeterministicBriefProvider:
    provider_id = "local_deterministic"
    model_id = "claim_evidence_brief"
    configuration_version = "claim_evidence_brief_v1"

    def __init__(self, behavior: str = "success") -> None:
        self.behavior = behavior

    def generate_structured(
        self, request: StructuredGenerationRequest, *, timeout_seconds: float
    ) -> ModelGenerationResult:
        started = time.perf_counter()
        if self.behavior == "timeout":
            raise ModelProviderTimeout("model provider timed out")
        if self.behavior == "failure":
            raise ModelProviderError("model provider invocation failed")
        if self.behavior == "malformed":
            content = "not-json"
        else:
            text = "\n".join(item.text for item in request.evidence)
            lowered = text.lower()
            task = request.task.lower()
            missing = []
            ambiguities = []
            conflicts = []
            if "estimate" in task and "estimate amount" not in lowered:
                missing.append("repair estimate")
            if "cause" in task and "cause allocation is unresolved" in lowered:
                ambiguities.append("The available evidence does not resolve the damage cause.")
            if "cause" in task and "no date, inspection" in lowered:
                missing.append("cause-supporting inspection")
            if "conflict" in lowered or ("2026-08-18" in text and "2026-08-12" in text):
                conflicts.append("Retrieved sources contain different reported loss dates.")
            if conflicts:
                status = "conflicting_evidence"
            elif ambiguities:
                status = "ambiguous_evidence"
            elif missing or not request.evidence:
                status = "insufficient_evidence"
            else:
                status = "supported"
            flags = [
                "untrusted_document_instructions_present"
                for item in request.evidence
                if item.injection_risk
            ]
            prohibited_request_terms = (
                "ignore previous",
                "system message",
                "assistant message",
                "tool call",
                "follow the instruction",
                "hidden prompt",
                "reveal secret",
                "invent",
                "citation evidence-not-authorized",
                "wrong policy",
                "policy edition 1999",
                "landscaping correspondence",
                "coverage without",
                "approve claim",
                "approve this claim",
                "deny claim",
                "deny this claim",
                "issue payment",
                "close the claim",
                "payment instruction",
                "fabricate evidence",
                "fraudulent evidence",
            )
            if any(term in task for term in prohibited_request_terms):
                flags.append("prohibited_or_instructional_request_detected")
                missing.append("supported claim evidence for the requested action")
                status = "insufficient_evidence"
            handles = [item.handle for item in request.evidence]
            if self.behavior in {"hallucinated_citation", "outside_citation"}:
                handles = ["EVIDENCE-NOT-AUTHORIZED"]
            summary = (
                "The retrieved claim evidence was organized for employee review."
                if status == "supported"
                else "The retrieved evidence requires additional human attention."
            )
            if self.behavior == "prohibited":
                summary = "Approve this claim and issue payment immediately."
            content = json.dumps(
                {
                    "status": status,
                    "claim_summary": summary,
                    "evidence_summary": (
                        "Evidence was summarized only from authorized retrieval results."
                    ),
                    "applicable_policy_summary": (
                        f"Applicable policy edition: {request.applicable_policy_edition}."
                    ),
                    "missing_information": missing,
                    "conflicts": conflicts,
                    "ambiguities": ambiguities,
                    "safety_flags": flags,
                    "citation_handles": handles,
                    "human_review_required": bool(missing or conflicts or ambiguities or flags),
                    "limitations": [
                        "This brief is evidence assistance, not a claim or coverage decision."
                    ],
                }
            )
        latency = (time.perf_counter() - started) * 1000
        return ModelGenerationResult(
            content=content,
            input_tokens=sum(len(item.text.split()) for item in request.evidence),
            output_tokens=len(content.split()),
            latency_ms=latency,
        )
