# app/worker.py
import asyncio

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

        job = service.mark_running(job_id)
        try:
            result = await processor.process(job)
        except Exception as exc:
            service.mark_failed_or_retry(job_id, str(exc))
        else:
            service.mark_completed(job_id, result)
