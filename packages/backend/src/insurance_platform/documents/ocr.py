from __future__ import annotations

from typing import Protocol


class OcrUnavailableError(RuntimeError):
    pass


class OcrAdapter(Protocol):
    name: str
    version: str

    async def extract_pages(self, content: bytes) -> list[str]: ...


class UnavailableOcrAdapter:
    """Explicit boundary for a future local OCR or Amazon Textract adapter."""

    name = "unavailable"
    version = "phase-2-boundary"

    async def extract_pages(self, content: bytes) -> list[str]:
        del content
        raise OcrUnavailableError("OCR is not configured; no OCR result was produced")


class SyntheticFixtureOcrAdapter:
    """Deterministic test-only OCR fixture; it never claims to process arbitrary scans."""

    name = "synthetic_fixture_ocr"
    version = "1"

    def __init__(self, expected_content: bytes, pages: list[str]) -> None:
        self._expected_content = expected_content
        self._pages = pages

    async def extract_pages(self, content: bytes) -> list[str]:
        if content != self._expected_content:
            raise OcrUnavailableError("fixture OCR received content outside its declared fixture")
        return list(self._pages)
