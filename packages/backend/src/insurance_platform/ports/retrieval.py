from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EmbeddingDescriptor:
    provider: str
    model: str
    version: str
    dimensions: int


class EmbeddingProvider(Protocol):
    @property
    def descriptor(self) -> EmbeddingDescriptor: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass(frozen=True, slots=True)
class SearchCandidate:
    chunk_id: UUID
    lexical_score: float
    vector_score: float


class VectorIndex(Protocol):
    def search(
        self,
        *,
        tenant_id: UUID,
        claim_id: UUID,
        query: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[SearchCandidate]: ...


class GenerationProvider(Protocol):
    provider: str
    model: str
    version: str

    def generate(self, *, question: str, evidence: list[str], state: str) -> str: ...
