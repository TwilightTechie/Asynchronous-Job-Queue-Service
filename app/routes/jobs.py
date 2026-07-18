from uuid import UUID

from fastapi import APIRouter, Request, status

from app.schemas import JobCreateRequest, JobCreateResponse, JobResponse

router = APIRouter()


@router.post("/jobs", status_code=status.HTTP_201_CREATED, response_model=JobCreateResponse)
async def create_job(payload: JobCreateRequest, request: Request) -> JobCreateResponse:
    job = request.app.state.job_service.submit_job(payload.type, payload.input)
    return JobCreateResponse(id=job.id, status=job.status, created_at=job.created_at)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, request: Request) -> JobResponse:
    job = request.app.state.job_service.get_job(job_id)
    return JobResponse(**job.model_dump())
