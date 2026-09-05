from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import Any

from redis.asyncio import Redis

from insurance_platform.ports.queue import Job


class InMemoryJobQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._results: dict[str, dict[str, Any]] = {}

    async def healthcheck(self) -> bool:
        return True

    async def enqueue(self, job: Job) -> None:
        await self._queue.put(job)

    async def dequeue(self, timeout_seconds: int = 5) -> Job | None:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout_seconds)
        except TimeoutError:
            return None

    async def complete(self, job: Job, result: dict[str, Any]) -> None:
        self._results[job.id] = result

    async def result(self, job_id: str) -> dict[str, Any] | None:
        return self._results.get(job_id)


class RedisJobQueue:
    def __init__(self, redis_url: str, queue_name: str) -> None:
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._queue_name = queue_name

    async def healthcheck(self) -> bool:
        return bool(await self._redis.ping())

    async def enqueue(self, job: Job) -> None:
        await self._redis.rpush(self._queue_name, json.dumps(asdict(job)))

    async def dequeue(self, timeout_seconds: int = 5) -> Job | None:
        item = await self._redis.blpop(self._queue_name, timeout=timeout_seconds)
        if item is None:
            return None
        _, payload = item
        data = json.loads(payload)
        return Job(**data)

    async def complete(self, job: Job, result: dict[str, Any]) -> None:
        key = f"{self._queue_name}:result:{job.id}"
        await self._redis.set(key, json.dumps(result), ex=3600, nx=True)

    async def result(self, job_id: str) -> dict[str, Any] | None:
        value = await self._redis.get(f"{self._queue_name}:result:{job_id}")
        return json.loads(value) if value else None
