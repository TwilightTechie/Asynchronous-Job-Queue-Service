from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models import JobStatus, JobType


class JobCreateRequest(BaseModel):
    type: JobType
    input: dict


class JobCreateResponse(BaseModel):
    id: UUID
    status: JobStatus
    created_at: datetime


class JobResponse(BaseModel):
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


class JobListResponse(BaseModel):
    jobs: list[JobResponse]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
