import asyncio
import uuid
from datetime import UTC, datetime

import pytest

from app.models import Job, JobStatus, JobType
from app.processor import MockProcessor


def _make_job() -> Job:
    now = datetime.now(UTC)
    return Job(
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


def test_mock_processor_succeeds_when_failure_rate_is_zero():
    processor = MockProcessor(min_sleep_seconds=0, max_sleep_seconds=0, failure_rate=0.0)

    result = asyncio.run(processor.process(_make_job()))

    assert "message" in result
    assert "duration_seconds" in result


def test_mock_processor_fails_when_failure_rate_is_one():
    processor = MockProcessor(min_sleep_seconds=0, max_sleep_seconds=0, failure_rate=1.0)

    with pytest.raises(RuntimeError):
        asyncio.run(processor.process(_make_job()))
