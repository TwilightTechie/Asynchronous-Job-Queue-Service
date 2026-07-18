import asyncio

from app.models import JobStatus, JobType
from app.processor import MockProcessor
from app.queue import AsyncioJobQueue
from app.repository import InMemoryJobRepository
from app.service import JobService
from app.worker import run_worker


def test_worker_processes_a_job_to_completion():
    async def scenario():
        repo = InMemoryJobRepository()
        queue = AsyncioJobQueue()
        service = JobService(repository=repo, queue=queue, max_attempts=3)
        processor = MockProcessor(min_sleep_seconds=0, max_sleep_seconds=0, failure_rate=0.0)
        stop_event = asyncio.Event()

        job = service.submit_job(JobType.REPORT, {})
        worker_task = asyncio.create_task(run_worker(queue, service, processor, stop_event))

        for _ in range(50):
            await asyncio.sleep(0.02)
            if repo.get(job.id).status == JobStatus.COMPLETED:
                break

        stop_event.set()
        await asyncio.wait_for(worker_task, timeout=2)

        final = repo.get(job.id)
        assert final.status == JobStatus.COMPLETED
        assert final.result is not None

    asyncio.run(scenario())


def test_worker_retries_then_fails_after_max_attempts():
    async def scenario():
        repo = InMemoryJobRepository()
        queue = AsyncioJobQueue()
        service = JobService(repository=repo, queue=queue, max_attempts=2)
        processor = MockProcessor(min_sleep_seconds=0, max_sleep_seconds=0, failure_rate=1.0)
        stop_event = asyncio.Event()

        job = service.submit_job(JobType.EXPORT, {})
        worker_task = asyncio.create_task(run_worker(queue, service, processor, stop_event))

        for _ in range(50):
            await asyncio.sleep(0.02)
            current = repo.get(job.id)
            if current.status == JobStatus.FAILED:
                break

        stop_event.set()
        await asyncio.wait_for(worker_task, timeout=2)

        final = repo.get(job.id)
        assert final.status == JobStatus.FAILED
        assert final.attempts == 2
        assert final.error is not None

    asyncio.run(scenario())


def test_worker_records_job_failed_metric_only_on_final_failure():
    from prometheus_client import REGISTRY

    async def scenario():
        repo = InMemoryJobRepository()
        queue = AsyncioJobQueue()
        service = JobService(repository=repo, queue=queue, max_attempts=1)
        processor = MockProcessor(min_sleep_seconds=0, max_sleep_seconds=0, failure_rate=1.0)
        stop_event = asyncio.Event()

        before = REGISTRY.get_sample_value("jobs_failed_total") or 0.0

        job = service.submit_job(JobType.EXPORT, {})
        worker_task = asyncio.create_task(run_worker(queue, service, processor, stop_event))

        for _ in range(50):
            await asyncio.sleep(0.02)
            if repo.get(job.id).status == JobStatus.FAILED:
                break

        stop_event.set()
        await asyncio.wait_for(worker_task, timeout=2)

        after = REGISTRY.get_sample_value("jobs_failed_total") or 0.0
        assert after == before + 1.0

    asyncio.run(scenario())
