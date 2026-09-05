from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class RateLimiter(Protocol):
    def check(
        self, *, scope: str, subject: str, limit: int, window_seconds: int
    ) -> RateLimitDecision: ...
