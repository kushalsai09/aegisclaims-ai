from __future__ import annotations

import threading
import time

from redis import Redis

from insurance_platform.ports.rate_limit import RateLimitDecision


class InMemoryRateLimiter:
    """Deterministic fixed-window limiter for local development and tests."""

    def __init__(self) -> None:
        self._counts: dict[str, tuple[int, int]] = {}
        self._lock = threading.Lock()

    def check(
        self, *, scope: str, subject: str, limit: int, window_seconds: int
    ) -> RateLimitDecision:
        now = int(time.time())
        bucket = now // window_seconds
        key = f"{scope}:{subject}"
        with self._lock:
            stored_bucket, count = self._counts.get(key, (bucket, 0))
            if stored_bucket != bucket:
                count = 0
            count += 1
            self._counts[key] = (bucket, count)
        retry_after = window_seconds - (now % window_seconds)
        return RateLimitDecision(count <= limit, max(limit - count, 0), retry_after)


class RedisRateLimiter:
    """Shared fixed-window limiter; Redis failure rejects protected operations."""

    def __init__(self, redis_url: str, namespace: str = "insurance:rate") -> None:
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._namespace = namespace

    def check(
        self, *, scope: str, subject: str, limit: int, window_seconds: int
    ) -> RateLimitDecision:
        now = int(time.time())
        bucket = now // window_seconds
        key = f"{self._namespace}:{scope}:{subject}:{bucket}"
        pipeline = self._redis.pipeline(transaction=True)
        pipeline.incr(key)
        pipeline.expire(key, window_seconds + 1, nx=True)
        count, _ = pipeline.execute()
        retry_after = window_seconds - (now % window_seconds)
        numeric_count = int(count)
        return RateLimitDecision(numeric_count <= limit, max(limit - numeric_count, 0), retry_after)
