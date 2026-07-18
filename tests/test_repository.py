import uuid
from datetime import UTC, datetime

from app.models import Job, JobStatus, JobType
from app.repository import InMemoryJobRepository


def _make_job(**overrides) -> Job:
    now = datetime.now(UTC)
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


def test_list_returns_all_jobs_newest_first():
    repo = InMemoryJobRepository()
    older = _make_job(created_at=datetime(2026, 1, 1, tzinfo=UTC))
    newer = _make_job(created_at=datetime(2026, 1, 2, tzinfo=UTC))
    repo.save(older)
    repo.save(newer)

    result = repo.list()

    assert result == [newer, older]


def test_list_filters_by_status():
    repo = InMemoryJobRepository()
    queued = _make_job(status=JobStatus.QUEUED)
    completed = _make_job(status=JobStatus.COMPLETED)
    repo.save(queued)
    repo.save(completed)

    result = repo.list(status=JobStatus.COMPLETED)

    assert result == [completed]


def test_list_on_empty_repository_returns_empty_list():
    repo = InMemoryJobRepository()

    assert repo.list() == []
