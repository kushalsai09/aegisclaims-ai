import asyncio

from insurance_platform.delivery.worker import process_job
from insurance_platform.infrastructure.queue import InMemoryJobQueue
from insurance_platform.ports.queue import Job


def test_smoke_worker_job_is_processed_idempotently() -> None:
    async def exercise() -> None:
        queue = InMemoryJobQueue()
        job = Job(
            id="job-1",
            kind="platform.smoke",
            payload={"message": "walking skeleton"},
            correlation_id="correlation-1",
        )

        assert await process_job(job, queue) is True
        first_result = await queue.result(job.id)
        assert await process_job(job, queue) is True
        assert (
            await queue.result(job.id)
            == first_result
            == {
                "handled": True,
                "kind": "platform.smoke",
                "message": "walking skeleton",
                "correlation_id": "correlation-1",
            }
        )

    asyncio.run(exercise())


def test_worker_ignores_unknown_job_kinds() -> None:
    async def exercise() -> None:
        queue = InMemoryJobQueue()
        job = Job(
            id="job-2",
            kind="unsupported",
            payload={},
            correlation_id="correlation-2",
        )

        assert await process_job(job, queue) is False
        assert await queue.result(job.id) is None

    asyncio.run(exercise())
