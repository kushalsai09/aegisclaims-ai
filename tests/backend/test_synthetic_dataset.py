from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy import func, select

from insurance_platform.infrastructure.models import (
    ClaimModel,
    DocumentModel,
    FactConflictModel,
    HumanReviewTaskModel,
)
from insurance_platform.synthetic.generator import dataset_hashes, load_manifest, repository_root


def test_manifest_has_all_required_scenarios_and_is_deterministic() -> None:
    manifest = load_manifest()
    assert {scenario.key for scenario in manifest.scenarios} == {
        "straightforward_supported",
        "missing_document",
        "conflicting_evidence",
        "ambiguous_policy_language",
        "incorrect_policy_version",
        "ocr_noisy_document",
        "irrelevant_distractor",
        "prompt_injection_document",
        "unsupported_unanswerable",
        "mandatory_human_review",
    }
    assert dataset_hashes() == dataset_hashes()
    assert all(
        "SYNTHETIC DEMONSTRATION DATA" in page
        for scenario in manifest.scenarios
        for document in scenario.documents
        for page in document.pages
    )


def test_seed_manifest_can_be_discovered_from_container_working_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    runtime_root = tmp_path / "app"
    manifest_directory = runtime_root / "data/synthetic/manifests"
    manifest_directory.mkdir(parents=True)
    source = repository_root() / "data/synthetic/manifests/phase2-scenarios.json"
    (manifest_directory / source.name).write_bytes(source.read_bytes())

    monkeypatch.chdir(runtime_root)
    assert repository_root() == runtime_root
    assert load_manifest().dataset_version == "phase2-synthetic-v1"


def test_golden_dataset_covers_every_scenario_and_policy_version() -> None:
    root = repository_root()
    golden = json.loads((root / "data/golden/phase2-ground-truth.json").read_text())
    manifest = load_manifest()
    assert set(golden["scenarios"]) == {scenario.key for scenario in manifest.scenarios}
    assert golden["governing_policy_edition"] == manifest.policy.edition == "2026-SYN-A"
    assert golden["scenarios"]["conflicting_evidence"]["known_conflicts"] == ["reported_loss_date"]
    assert golden["scenarios"]["prompt_injection_document"]["content_authority"] == (
        "untrusted_data_only"
    )


def test_policy_material_is_fictional_and_every_rule_is_labeled() -> None:
    policy = (
        repository_root() / "data/synthetic/product/harborview-homesecure-2026-syn-a.md"
    ).read_text()
    assert "not copied from" in policy
    assert policy.count("SYNTHETIC DEMONSTRATION RULE") >= 15
    assert "HO-SYN-01" in policy and "2026-SYN-A" in policy


def test_synthetic_manifest_contains_no_common_real_pii_patterns() -> None:
    source = (repository_root() / "data/synthetic/manifests/phase2-scenarios.json").read_text()
    assert not re.search(r"\b\d{3}-\d{2}-\d{4}\b", source)
    assert not re.search(r"\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b", source)
    assert "@gmail.com" not in source.lower()


def test_seeded_phase2_domain_has_expected_counts_and_safety_cases(client) -> None:  # type: ignore[no-untyped-def]
    with client.app.state.components.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ClaimModel)) == 10
        assert session.scalar(select(func.count()).select_from(DocumentModel)) == 15
        assert session.scalar(select(func.count()).select_from(HumanReviewTaskModel)) == 5
        conflicts = list(session.scalars(select(FactConflictModel)))
        assert any(conflict.fact_type == "reported_loss_date" for conflict in conflicts)
        injection = session.scalar(
            select(DocumentModel).where(DocumentModel.injection_risk.is_(True))
        )
        assert injection is not None
        ocr_fixture = session.scalar(
            select(DocumentModel).where(DocumentModel.name == "Synthetic OCR Fixture Notice.pdf")
        )
        assert ocr_fixture is not None
        assert ocr_fixture.pages[0].extraction_method == "synthetic_fixture_ocr_v1"
