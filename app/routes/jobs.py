from uuid import UUID

from fastapi import APIRouter, Request, status

from app.models import JobStatus
from app.observability.metrics import record_job_submitted
from app.schemas import JobCreateRequest, JobCreateResponse, JobListResponse, JobResponse

router = APIRouter()


@router.post("/jobs", status_code=status.HTTP_201_CREATED, response_model=JobCreateResponse)
async def create_job(payload: JobCreateRequest, request: Request) -> JobCreateResponse:
    job = request.app.state.job_service.submit_job(payload.type, payload.input)
    record_job_submitted()
    return JobCreateResponse(id=job.id, status=job.status, created_at=job.created_at)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(request: Request, status: JobStatus | None = None) -> JobListResponse:
    jobs = request.app.state.job_service.list_jobs(status)
    return JobListResponse(jobs=[JobResponse(**job.model_dump()) for job in jobs])


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, request: Request) -> JobResponse:
    job = request.app.state.job_service.get_job(job_id)
    return JobResponse(**job.model_dump())
