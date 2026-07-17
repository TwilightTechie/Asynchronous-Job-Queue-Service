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


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
