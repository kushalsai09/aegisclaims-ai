from __future__ import annotations

import hashlib
import math
import re

from insurance_platform.ports.retrieval import EmbeddingDescriptor

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class DeterministicHashEmbeddingProvider:
    descriptor = EmbeddingDescriptor(
        provider="local_deterministic",
        model="signed_token_hash",
        version="signed_token_hash_64_v1",
        dimensions=64,
    )

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.descriptor.dimensions
        for token in TOKEN_PATTERN.findall(text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % len(vector)
            vector[index] += 1.0 if digest[4] % 2 == 0 else -1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector
