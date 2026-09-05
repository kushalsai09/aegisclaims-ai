from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas


class FixtureModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PolicyFixture(FixtureModel):
    identifier: str
    product_code: str
    edition: str
    effective_from: str
    effective_to: str


class DocumentFixture(FixtureModel):
    name: str
    expected_type: str
    pages: list[str] = Field(min_length=1)
    extraction_method: str = "pypdf_text_v1"
    injection_risk: bool = False


class ScenarioFixture(FixtureModel):
    key: str
    claim_number: str
    loss_date: str
    loss_type: str
    property_address: str
    description: str
    mandatory_human_review: bool
    documents: list[DocumentFixture] = Field(min_length=1)


class DatasetManifest(FixtureModel):
    dataset_version: str
    synthetic_label: str
    policy: PolicyFixture
    scenarios: list[ScenarioFixture] = Field(min_length=10)


def repository_root() -> Path:
    candidates = (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    for candidate in candidates:
        if (candidate / "data" / "synthetic").is_dir():
            return candidate
    raise RuntimeError("repository root containing synthetic data was not found")


def load_manifest() -> DatasetManifest:
    path = repository_root() / "data/synthetic/manifests/phase2-scenarios.json"
    return DatasetManifest.model_validate_json(path.read_text())


def render_text_pdf(document: DocumentFixture) -> bytes:
    output = BytesIO()
    canvas = Canvas(
        output,
        pagesize=letter,
        invariant=1,
        pageCompression=0,
    )
    canvas.setTitle(document.name)
    canvas.setAuthor("HarborView Synthetic Data Generator")
    width, height = letter
    for page_number, page in enumerate(document.pages, start=1):
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(54, height - 40, "SYNTHETIC DEMONSTRATION DATA")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(width - 54, height - 40, f"Page {page_number}")
        y = height - 70
        for source_line in page.splitlines():
            lines = _wrap(source_line, "Helvetica", 10, width - 108) or [""]
            for line in lines:
                canvas.setFont("Helvetica", 10)
                canvas.drawString(54, y, line)
                y -= 15
                if y < 54:
                    canvas.showPage()
                    y = height - 54
        canvas.showPage()
    canvas.save()
    return output.getvalue()


def _wrap(text: str, font: str, size: int, maximum: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and stringWidth(candidate, font, size) > maximum:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def dataset_hashes() -> dict[str, str]:
    manifest = load_manifest()
    result: dict[str, str] = {}
    for scenario in manifest.scenarios:
        for document in scenario.documents:
            key = f"{scenario.key}/{document.name}"
            result[key] = hashlib.sha256(render_text_pdf(document)).hexdigest()
    return result


def write_generated_documents(output_directory: Path) -> dict[str, str]:
    manifest = load_manifest()
    hashes: dict[str, str] = {}
    for scenario in manifest.scenarios:
        directory = output_directory / scenario.key
        directory.mkdir(parents=True, exist_ok=True)
        for document in scenario.documents:
            content = render_text_pdf(document)
            path = directory / document.name
            path.write_bytes(content)
            hashes[str(path.relative_to(output_directory))] = hashlib.sha256(content).hexdigest()
    (output_directory / "sha256-manifest.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n"
    )
    return hashes
