from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class JobType(str, Enum):
    REPORT = "report"
    TRANSCODE = "transcode"
    EXPORT = "export"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(BaseModel):
    id: UUID
    type: JobType
    input: dict
    status: JobStatus
    result: dict | None
    error: str | None
    attempts: int
    max_attempts: int
    created_at: datetime
    updated_at: datetime
