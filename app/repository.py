from typing import Protocol
from uuid import UUID

from app.models import Job, JobStatus


class JobRepository(Protocol):
    def save(self, job: Job) -> None: ...

    def get(self, job_id: UUID) -> Job | None: ...

    def list(self, status: JobStatus | None = None) -> list[Job]: ...


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[UUID, Job] = {}

    def save(self, job: Job) -> None:
        self._jobs[job.id] = job

    def get(self, job_id: UUID) -> Job | None:
        return self._jobs.get(job_id)

    def list(self, status: JobStatus | None = None) -> list[Job]:
        jobs = [job for job in self._jobs.values() if status is None or job.status == status]
        return sorted(jobs, key=lambda job: job.created_at, reverse=True)
