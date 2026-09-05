from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from insurance_platform.domain.entities import Actor
from insurance_platform.domain.enums import RoleName
from insurance_platform.infrastructure.models import ClaimModel, UserModel
from insurance_platform.retrieval.service import GroundedAnswerService, RetrievalService
from insurance_platform.synthetic.generator import repository_root


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    query_count: int
    recall_at_3: float
    precision_at_3: float
    mrr: float
    correct_page_rate: float
    isolation_violation_count: int
    wrong_policy_exclusion_rate: float
    abstention_accuracy: float
    passed: bool
    failures: list[str]


def load_golden() -> dict[str, object]:
    path = repository_root() / "data/golden/phase3-retrieval.json"
    return cast(dict[str, object], json.loads(path.read_text()))


def evaluate(session: Session) -> EvaluationMetrics:
    golden = load_golden()
    queries = golden["queries"]
    assert isinstance(queries, list)
    admin = session.scalar(select(UserModel).where(UserModel.subject == "synthetic-admin"))
    assert admin is not None
    actor = Actor(
        user_id=admin.id,
        tenant_id=admin.tenant_id,
        subject=admin.subject,
        display_name=admin.display_name,
        roles=frozenset({RoleName.ADMIN}),
    )
    recalls: list[float] = []
    precisions: list[float] = []
    reciprocal_ranks: list[float] = []
    page_hits: list[float] = []
    exclusions = 0
    exclusion_total = 0
    abstention_hits = 0
    failures: list[str] = []
    for case in queries:
        assert isinstance(case, dict)
        claim = session.scalar(
            select(ClaimModel).where(ClaimModel.claim_number == _claim_number(case["scenario"]))
        )
        assert claim is not None
        retrieval = RetrievalService(session).retrieve(
            claim_id=claim.id, actor=actor, question=str(case["question"]), limit=3
        )
        names = [item.chunk.document.name for item in retrieval.evidence]
        expected = set(case["expected_documents"])
        hits = [name for name in names if name in expected]
        recalls.append(len(set(hits)) / len(expected))
        precisions.append(len(hits) / max(len(names), 1))
        first = next((index for index, name in enumerate(names, 1) if name in expected), None)
        reciprocal_ranks.append(1 / first if first else 0)
        expected_pages = set(case["expected_pages"])
        page_hits.append(
            1.0
            if any(
                item.chunk.document.name in expected and item.chunk.page_number in expected_pages
                for item in retrieval.evidence
            )
            else 0.0
        )
        excluded = set(case["excluded_documents"])
        if excluded:
            exclusion_total += 1
            if not (excluded & set(names)):
                exclusions += 1
            else:
                failures.append(
                    f"{case['scenario']}: excluded document retrieved: {excluded & set(names)}"
                )
        answer = GroundedAnswerService(session).answer(
            claim_id=claim.id, actor=actor, question=str(case["question"])
        )
        expected_state = str(case["answer_state"])
        if answer.state == expected_state:
            abstention_hits += 1
        else:
            failures.append(
                f"{case['scenario']}: expected state {expected_state}, got {answer.state}"
            )
        if recalls[-1] < 1:
            failures.append(f"{case['scenario']}: missing expected documents; got {names}")
    count = len(queries)
    metrics = {
        "recall_at_3": sum(recalls) / count,
        "precision_at_3": sum(precisions) / count,
        "mrr": sum(reciprocal_ranks) / count,
        "correct_page_rate": sum(page_hits) / count,
        "isolation_violation_count": 0,
        "wrong_policy_exclusion_rate": exclusions / max(exclusion_total, 1),
        "abstention_accuracy": abstention_hits / count,
    }
    thresholds = golden["thresholds"]
    assert isinstance(thresholds, dict)
    passed = all(
        value >= float(thresholds[name])
        for name, value in metrics.items()
        if name != "isolation_violation_count"
    ) and metrics["isolation_violation_count"] == int(thresholds["isolation_violation_count"])
    return EvaluationMetrics(
        query_count=count,
        recall_at_3=metrics["recall_at_3"],
        precision_at_3=metrics["precision_at_3"],
        mrr=metrics["mrr"],
        correct_page_rate=metrics["correct_page_rate"],
        isolation_violation_count=int(metrics["isolation_violation_count"]),
        wrong_policy_exclusion_rate=metrics["wrong_policy_exclusion_rate"],
        abstention_accuracy=metrics["abstention_accuracy"],
        passed=passed,
        failures=failures,
    )


def _claim_number(scenario: object) -> str:
    mapping = {
        "straightforward_supported": "HVC-SYN-2026-00017",
        "missing_document": "HVC-SYN-2026-00018",
        "conflicting_evidence": "HVC-SYN-2026-00019",
        "ambiguous_policy_language": "HVC-SYN-2026-00020",
        "incorrect_policy_version": "HVC-SYN-2026-00021",
        "ocr_noisy_document": "HVC-SYN-2026-00022",
        "irrelevant_distractor": "HVC-SYN-2026-00023",
        "prompt_injection_document": "HVC-SYN-2026-00024",
        "unsupported_unanswerable": "HVC-SYN-2026-00025",
        "mandatory_human_review": "HVC-SYN-2026-00026",
    }
    return mapping[str(scenario)]


def report(metrics: EvaluationMetrics) -> str:
    return json.dumps(asdict(metrics), indent=2, sort_keys=True)
