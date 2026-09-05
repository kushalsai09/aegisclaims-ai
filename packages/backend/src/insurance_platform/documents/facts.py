from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractedFact:
    page_number: int
    fact_type: str
    raw_source_span: str
    normalized_value: str


FACT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("reported_loss_date", re.compile(r"(?im)^reported loss date:\s*([^\r\n]+)")),
    ("inspection_date", re.compile(r"(?im)^inspection date:\s*([^\r\n]+)")),
    ("loss_type", re.compile(r"(?im)^loss type:\s*([^\r\n]+)")),
    ("property_address", re.compile(r"(?im)^property address:\s*([^\r\n]+)")),
    ("policy_identifier", re.compile(r"(?im)^policy identifier:\s*([^\r\n]+)")),
    ("policy_edition", re.compile(r"(?im)^policy edition:\s*([^\r\n]+)")),
    ("estimate_amount", re.compile(r"(?im)^estimate amount:\s*\$?([^\r\n]+)")),
    ("contractor_identity", re.compile(r"(?im)^contractor:\s*([^\r\n]+)")),
    ("reported_damage", re.compile(r"(?im)^reported damage:\s*([^\r\n]+)")),
)


def extract_structured_facts(pages: list[str]) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    for page_number, text in enumerate(pages, start=1):
        for fact_type, pattern in FACT_PATTERNS:
            for match in pattern.finditer(text):
                raw = match.group(0).strip()
                value = " ".join(match.group(1).strip().split())
                if fact_type in {"policy_identifier", "policy_edition"}:
                    value = value.upper()
                facts.append(ExtractedFact(page_number, fact_type, raw, value))
    return facts
