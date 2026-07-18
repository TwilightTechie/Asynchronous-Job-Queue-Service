from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.observability.metrics import set_queue_depth

router = APIRouter()


@router.get("/metrics")
async def metrics(request: Request) -> Response:
    set_queue_depth(request.app.state.job_queue.qsize())
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
