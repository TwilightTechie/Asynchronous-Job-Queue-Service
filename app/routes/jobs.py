from fastapi import APIRouter, Request, status

from app.schemas import JobCreateRequest, JobCreateResponse

router = APIRouter()


@router.post("/jobs", status_code=status.HTTP_201_CREATED, response_model=JobCreateResponse)
async def create_job(payload: JobCreateRequest, request: Request) -> JobCreateResponse:
    job = request.app.state.job_service.submit_job(payload.type, payload.input)
    return JobCreateResponse(id=job.id, status=job.status, created_at=job.created_at)
