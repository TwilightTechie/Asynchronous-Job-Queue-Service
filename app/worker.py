# app/worker.py
import asyncio
import time

from app.models import JobStatus
from app.observability.metrics import record_job_completed, record_job_failed
from app.processor import JobProcessor
from app.queue import JobQueue
from app.service import JobService


async def run_worker(
    queue: JobQueue,
    service: JobService,
    processor: JobProcessor,
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        try:
            job_id = await asyncio.wait_for(queue.get(), timeout=0.5)
        except TimeoutError:
            continue

        if stop_event.is_set():
            break

        job = service.mark_running(job_id)
        start = time.perf_counter()
        try:
            result = await processor.process(job)
        except Exception as exc:
            updated = service.mark_failed_or_retry(job_id, str(exc))
            if updated.status == JobStatus.FAILED:
                record_job_failed()
        else:
            duration_seconds = time.perf_counter() - start
            service.mark_completed(job_id, result)
            record_job_completed(duration_seconds)
