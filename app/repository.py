from typing import Protocol
from uuid import UUID

from app.models import Job


class JobRepository(Protocol):
    def save(self, job: Job) -> None: ...

    def get(self, job_id: UUID) -> Job | None: ...


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[UUID, Job] = {}

    def save(self, job: Job) -> None:
        self._jobs[job.id] = job

    def get(self, job_id: UUID) -> Job | None:
        return self._jobs.get(job_id)
