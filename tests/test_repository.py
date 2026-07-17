import uuid
from datetime import datetime, timezone

from app.models import Job, JobStatus, JobType
from app.repository import InMemoryJobRepository


def _make_job(**overrides) -> Job:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        type=JobType.REPORT,
        input={},
        status=JobStatus.QUEUED,
        result=None,
        error=None,
        attempts=0,
        max_attempts=3,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return Job(**defaults)


def test_save_then_get_returns_the_job():
    repo = InMemoryJobRepository()
    job = _make_job()

    repo.save(job)

    assert repo.get(job.id) == job


def test_get_unknown_id_returns_none():
    repo = InMemoryJobRepository()

    assert repo.get(uuid.uuid4()) is None


def test_save_overwrites_existing_job():
    repo = InMemoryJobRepository()
    job = _make_job()
    repo.save(job)

    updated = job.model_copy(update={"status": JobStatus.RUNNING})
    repo.save(updated)

    assert repo.get(job.id).status == JobStatus.RUNNING
