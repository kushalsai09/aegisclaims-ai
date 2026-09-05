from __future__ import annotations

import re

INJECTION_MARKERS = (
    "ignore previous instructions",
    "approve this claim",
    "reveal the system prompt",
    "call the tool",
    "change permissions",
)
STOP_WORDS = {"a", "an", "and", "are", "in", "is", "of", "on", "the", "this", "to", "what", "which"}


class DeterministicGroundedGenerationProvider:
    provider = "local_deterministic"
    model = "extractive_grounded_answer"
    version = "extractive_grounded_answer_v1"

    def generate(self, *, question: str, evidence: list[str], state: str) -> str:
        if state == "insufficient_evidence":
            return "The available claim evidence is insufficient to answer this question."
        if state == "conflicting_evidence":
            return (
                "The available documents contain conflicting evidence. Human review is required; "
                "neither value was selected automatically."
            )
        if state == "ambiguous_evidence":
            return (
                "The retrieved evidence explicitly leaves this issue unresolved. "
                "Human interpretation is required."
            )
        query_tokens = set(re.findall(r"[a-z0-9]+", question.lower())) - STOP_WORDS
        candidates: list[tuple[int, str]] = []
        for passage in evidence:
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", passage):
                clean = sentence.strip()
                lower = clean.lower()
                if not clean or any(marker in lower for marker in INJECTION_MARKERS):
                    continue
                overlap = len(query_tokens & set(re.findall(r"[a-z0-9]+", lower)))
                if "rule" in query_tokens and "synthetic demonstration rule" in lower:
                    overlap += 5
                candidates.append((overlap, clean))
        candidates.sort(key=lambda item: (-item[0], item[1]))
        selected = [text for score, text in candidates if score > 0][:1]
        if not selected:
            return "The retrieved evidence does not contain a sufficiently supported answer."
        return "Grounded evidence: " + " ".join(selected)
