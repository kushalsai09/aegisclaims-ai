from __future__ import annotations

import asyncio
import signal

import structlog

from insurance_platform.config import get_settings
from insurance_platform.delivery.components import build_components
from insurance_platform.observability.logging import configure_logging
from insurance_platform.observability.metrics import WORKER_FAILURES
from insurance_platform.ports.queue import Job, JobQueue


async def process_job(job: Job, queue: JobQueue) -> bool:
    """Process one supported job and persist a deterministic result."""
    if job.kind != "platform.smoke":
        return False
    await queue.complete(
        job,
        {
            "handled": True,
            "kind": job.kind,
            "message": job.payload.get("message"),
            "correlation_id": job.correlation_id,
        },
    )
    return True


async def run(stop_event: asyncio.Event | None = None) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    components = build_components(settings)
    logger = structlog.get_logger().bind(service="insurance-worker")
    logger.info("worker_started", queue=settings.queue_name)
    stopping = stop_event or asyncio.Event()
    while not stopping.is_set():
        try:
            job = await components.job_queue.dequeue(timeout_seconds=2)
        except Exception:
            WORKER_FAILURES.labels(stage="dequeue").inc()
            logger.exception("worker_dependency_unavailable", stage="dequeue")
            await asyncio.sleep(1)
            continue
        if job is None:
            continue
        try:
            if await process_job(job, components.job_queue):
                logger.info("job_completed", job_id=job.id, kind=job.kind)
            else:
                logger.warning("job_ignored", job_id=job.id, kind=job.kind)
        except Exception:
            WORKER_FAILURES.labels(stage="process").inc()
            logger.exception("job_failed", job_id=job.id, kind=job.kind)
    logger.info("worker_stopped")


async def _main() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for stop_signal in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(stop_signal, stop_event.set)
    await run(stop_event)


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
