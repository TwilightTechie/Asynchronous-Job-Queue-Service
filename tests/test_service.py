import asyncio

import pytest

from app.exceptions import JobNotFoundError
from app.models import JobStatus, JobType
from app.queue import AsyncioJobQueue
from app.repository import InMemoryJobRepository
from app.service import JobService


def _make_service(
    max_attempts: int = 3,
) -> tuple[JobService, InMemoryJobRepository, AsyncioJobQueue]:
    repo = InMemoryJobRepository()
    queue = AsyncioJobQueue()
    service = JobService(repository=repo, queue=queue, max_attempts=max_attempts)
    return service, repo, queue


def test_submit_job_creates_queued_job_with_configured_max_attempts():
    service, _repo, _queue = _make_service(max_attempts=3)

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
    service, repo, _queue = _make_service()

    job = service.submit_job(JobType.EXPORT, {})

    assert repo.get(job.id) == job


def test_submit_job_generates_unique_ids():
    service, _repo, _queue = _make_service()

    job1 = service.submit_job(JobType.TRANSCODE, {})
    job2 = service.submit_job(JobType.TRANSCODE, {})

    assert job1.id != job2.id


def test_submit_job_enqueues_the_job_id():
    service, _repo, queue = _make_service()

    job = service.submit_job(JobType.REPORT, {})

    assert asyncio.run(queue.get()) == job.id


def test_get_job_returns_the_job():
    service, _repo, _queue = _make_service()
    job = service.submit_job(JobType.REPORT, {})

    assert service.get_job(job.id) == job


def test_get_job_raises_job_not_found_for_unknown_id():
    service, _repo, _queue = _make_service()

    with pytest.raises(JobNotFoundError):
        service.get_job(__import__("uuid").uuid4())


def test_list_jobs_returns_all_by_default():
    service, _repo, _queue = _make_service()
    job1 = service.submit_job(JobType.REPORT, {})
    job2 = service.submit_job(JobType.EXPORT, {})

    result = service.list_jobs()

    assert {j.id for j in result} == {job1.id, job2.id}


def test_mark_running_transitions_status():
    service, _repo, _queue = _make_service()
    job = service.submit_job(JobType.REPORT, {})

    updated = service.mark_running(job.id)

    assert updated.status == JobStatus.RUNNING
    assert service.get_job(job.id).status == JobStatus.RUNNING


def test_mark_completed_sets_result_and_status():
    service, _repo, _queue = _make_service()
    job = service.submit_job(JobType.REPORT, {})
    service.mark_running(job.id)

    updated = service.mark_completed(job.id, {"message": "done"})

    assert updated.status == JobStatus.COMPLETED
    assert updated.result == {"message": "done"}


def test_mark_failed_or_retry_requeues_when_attempts_remain():
    service, _repo, queue = _make_service(max_attempts=3)
    job = service.submit_job(JobType.REPORT, {})
    asyncio.run(queue.get())  # drain the initial enqueue from submit_job
    service.mark_running(job.id)

    updated = service.mark_failed_or_retry(job.id, "boom")

    assert updated.status == JobStatus.QUEUED
    assert updated.attempts == 1
    assert asyncio.run(queue.get()) == job.id


def test_mark_failed_or_retry_fails_when_attempts_exhausted():
    service, _repo, queue = _make_service(max_attempts=1)
    job = service.submit_job(JobType.REPORT, {})
    asyncio.run(queue.get())
    service.mark_running(job.id)

    updated = service.mark_failed_or_retry(job.id, "boom")

    assert updated.status == JobStatus.FAILED
    assert updated.attempts == 1
    assert updated.error == "boom"
