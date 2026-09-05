from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class Job:
    id: str
    kind: str
    payload: dict[str, Any]
    correlation_id: str


class JobQueue(Protocol):
    async def healthcheck(self) -> bool: ...

    async def enqueue(self, job: Job) -> None: ...

    async def dequeue(self, timeout_seconds: int = 5) -> Job | None: ...

    async def complete(self, job: Job, result: dict[str, Any]) -> None: ...

    async def result(self, job_id: str) -> dict[str, Any] | None: ...
