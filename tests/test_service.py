from app.models import JobStatus, JobType
from app.repository import InMemoryJobRepository
from app.service import JobService


def test_submit_job_creates_queued_job_with_configured_max_attempts():
    repo = InMemoryJobRepository()
    service = JobService(repository=repo, max_attempts=3)

    job = service.submit_job(JobType.REPORT, {"customer_id": "abc123"})

    assert job.type == JobType.REPORT
    assert job.input == {"customer_id": "abc123"}
    assert job.status == JobStatus.QUEUED
    assert job.attempts == 0
    assert job.max_attempts == 3
    assert job.result is None
    assert job.error is None
    assert job.created_at == job.updated_at


def test_submit_job_persists_to_repository():
    repo = InMemoryJobRepository()
    service = JobService(repository=repo, max_attempts=3)

    job = service.submit_job(JobType.EXPORT, {})

    assert repo.get(job.id) == job


def test_submit_job_generates_unique_ids():
    repo = InMemoryJobRepository()
    service = JobService(repository=repo, max_attempts=3)

    job1 = service.submit_job(JobType.TRANSCODE, {})
    job2 = service.submit_job(JobType.TRANSCODE, {})

    assert job1.id != job2.id
