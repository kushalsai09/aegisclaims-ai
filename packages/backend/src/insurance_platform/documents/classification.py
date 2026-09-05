from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Classification:
    document_type: str
    method: str
    version: str
    signals: dict[str, list[str]]


CATEGORY_SIGNALS: dict[str, tuple[str, ...]] = {
    "notice_of_loss": ("first notice of loss", "notice of loss", "reported loss date"),
    "contractor_estimate": ("contractor estimate", "estimate amount", "contractor:"),
    "inspection_report": ("inspection report", "inspection date", "inspector"),
    "policyholder_statement": ("policyholder statement", "statement of loss"),
    "policy_document": ("homesecure", "policy identifier", "coverage sections"),
    "correspondence": ("correspondence", "subject:", "dear claims"),
    "weather_evidence": ("weather event", "wind speed", "event evidence"),
    "property_damage_report": ("damage report", "reported damage"),
}


def classify_document(filename: str, pages: list[str]) -> Classification:
    corpus = f"{filename}\n{' '.join(pages)}".lower()
    matches = {
        category: [signal for signal in signals if signal in corpus]
        for category, signals in CATEGORY_SIGNALS.items()
    }
    matches = {category: signals for category, signals in matches.items() if signals}
    if not matches:
        return Classification("other", "deterministic_rules", "1", {})
    category = max(matches, key=lambda key: (len(matches[key]), key))
    return Classification(category, "deterministic_rules", "1", matches)


def detect_injection_risk(pages: list[str]) -> bool:
    corpus = " ".join(pages).lower()
    indicators = (
        "ignore previous instructions",
        "ignore all instructions",
        "approve this claim",
        "call the tool",
        "system prompt",
    )
    return any(indicator in corpus for indicator in indicators)
