import uuid
from datetime import datetime, timezone

from app.models import Job, JobStatus, JobType
from app.repository import JobRepository


class JobService:
    def __init__(self, repository: JobRepository, max_attempts: int) -> None:
        self._repository = repository
        self._max_attempts = max_attempts

    def submit_job(self, job_type: JobType, input: dict) -> Job:
        now = datetime.now(timezone.utc)
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
        return job
