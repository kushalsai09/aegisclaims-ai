from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

CHUNKER_VERSION = "page_window_chars_700_overlap_100_v1"
MAX_CHARS = 700
OVERLAP_CHARS = 100
CHUNK_NAMESPACE = uuid.UUID("3a510e21-1006-43af-8a73-9be5f8127d2a")


@dataclass(frozen=True, slots=True)
class DeterministicChunk:
    identifier: str
    ordinal: int
    text: str
    source_start: int
    source_end: int


def chunk_page(document_id: uuid.UUID, page_checksum: str, text: str) -> list[DeterministicChunk]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    chunks: list[DeterministicChunk] = []
    start = 0
    ordinal = 0
    while start < len(normalized):
        proposed_end = min(start + MAX_CHARS, len(normalized))
        end = proposed_end
        if proposed_end < len(normalized):
            boundary = max(
                normalized.rfind("\n", start + 1, proposed_end + 1),
                normalized.rfind(" ", start + 1, proposed_end + 1),
            )
            if boundary > start + MAX_CHARS // 2:
                end = boundary
        chunk_text = normalized[start:end].strip()
        actual_start = start
        while actual_start < end and normalized[actual_start].isspace():
            actual_start += 1
        actual_end = actual_start + len(chunk_text)
        digest_input = (
            f"{document_id}:{page_checksum}:{CHUNKER_VERSION}:{ordinal}:"
            f"{actual_start}:{actual_end}:{hashlib.sha256(chunk_text.encode()).hexdigest()}"
        )
        identifier = f"chunk-{uuid.uuid5(CHUNK_NAMESPACE, digest_input)}"
        chunks.append(DeterministicChunk(identifier, ordinal, chunk_text, actual_start, actual_end))
        ordinal += 1
        if end >= len(normalized):
            break
        start = max(end - OVERLAP_CHARS, start + 1)
    return chunks
