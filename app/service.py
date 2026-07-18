import uuid
from datetime import UTC, datetime
from uuid import UUID

from app.exceptions import JobNotFoundError
from app.models import Job, JobStatus, JobType
from app.queue import JobQueue
from app.repository import JobRepository


class JobService:
    def __init__(self, repository: JobRepository, queue: JobQueue, max_attempts: int) -> None:
        self._repository = repository
        self._queue = queue
        self._max_attempts = max_attempts

    def submit_job(self, job_type: JobType, input: dict) -> Job:
        now = datetime.now(UTC)
        job = Job(
            id=uuid.uuid4(),
            type=job_type,
            input=input,
            status=JobStatus.QUEUED,
            result=None,
            error=None,
            attempts=0,
            max_attempts=self._max_attempts,
            created_at=now,
            updated_at=now,
        )
        self._repository.save(job)
        self._queue.put_nowait(job.id)
        return job

    def get_job(self, job_id: UUID) -> Job:
        job = self._repository.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        return job

    def list_jobs(self, status: JobStatus | None = None) -> list[Job]:
        return self._repository.list(status)

    def mark_running(self, job_id: UUID) -> Job:
        job = self.get_job(job_id)
        updated = job.model_copy(
            update={"status": JobStatus.RUNNING, "updated_at": datetime.now(UTC)}
        )
        self._repository.save(updated)
        return updated

    def mark_completed(self, job_id: UUID, result: dict) -> Job:
        job = self.get_job(job_id)
        updated = job.model_copy(
            update={
                "status": JobStatus.COMPLETED,
                "result": result,
                "attempts": job.attempts + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        self._repository.save(updated)
        return updated

    def mark_failed_or_retry(self, job_id: UUID, error: str) -> Job:
        job = self.get_job(job_id)
        attempts = job.attempts + 1
        if attempts < job.max_attempts:
            updated = job.model_copy(
                update={
                    "status": JobStatus.QUEUED,
                    "attempts": attempts,
                    "updated_at": datetime.now(UTC),
                }
            )
            self._repository.save(updated)
            self._queue.put_nowait(job_id)
            return updated
        updated = job.model_copy(
            update={
                "status": JobStatus.FAILED,
                "attempts": attempts,
                "error": error,
                "updated_at": datetime.now(UTC),
            }
        )
        self._repository.save(updated)
        return updated
