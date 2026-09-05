from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from insurance_platform.documents.ocr import OcrAdapter, OcrUnavailableError


class DocumentExtractionError(RuntimeError):
    pass


async def extract_pages(
    content: bytes, detected_mime_type: str, ocr: OcrAdapter
) -> tuple[list[str], str]:
    if detected_mime_type == "text/plain":
        try:
            return [content.decode("utf-8")], "utf8_text_v1"
        except UnicodeDecodeError as exc:
            raise DocumentExtractionError("text document is not valid UTF-8") from exc
    try:
        reader = PdfReader(BytesIO(content), strict=True)
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception as exc:
        raise DocumentExtractionError("PDF parser could not safely extract this document") from exc
    if pages and any(page for page in pages):
        return pages, "pypdf_text_v1"
    try:
        return await ocr.extract_pages(content), f"{ocr.name}_{ocr.version}"
    except OcrUnavailableError as exc:
        raise DocumentExtractionError(str(exc)) from exc
