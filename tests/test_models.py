import uuid
from datetime import UTC, datetime

from app.models import Job, JobStatus, JobType


def test_job_type_values():
    assert JobType.REPORT == "report"
    assert JobType.TRANSCODE == "transcode"
    assert JobType.EXPORT == "export"


def test_job_status_values():
    assert JobStatus.QUEUED == "queued"
    assert JobStatus.RUNNING == "running"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"


def test_job_construction_defaults():
    now = datetime.now(UTC)
    job = Job(
        id=uuid.uuid4(),
        type=JobType.REPORT,
        input={"customer_id": "abc123"},
        status=JobStatus.QUEUED,
        result=None,
        error=None,
        attempts=0,
        max_attempts=3,
        created_at=now,
        updated_at=now,
    )
    assert job.status == JobStatus.QUEUED
    assert job.result is None
    assert job.error is None
    assert job.attempts == 0
