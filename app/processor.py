import asyncio
import random
from typing import Protocol

from app.models import Job


class JobProcessor(Protocol):
    async def process(self, job: Job) -> dict: ...


class MockProcessor:
    def __init__(
        self, min_sleep_seconds: float, max_sleep_seconds: float, failure_rate: float
    ) -> None:
        self._min_sleep_seconds = min_sleep_seconds
        self._max_sleep_seconds = max_sleep_seconds
        self._failure_rate = failure_rate

    async def process(self, job: Job) -> dict:
        duration = random.uniform(self._min_sleep_seconds, self._max_sleep_seconds)
        await asyncio.sleep(duration)
        if random.random() < self._failure_rate:
            raise RuntimeError("mock processing failed")
        return {
            "message": f"{job.type.value} job completed",
            "duration_seconds": round(duration, 2),
        }
