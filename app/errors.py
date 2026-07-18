import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions import JobNotFoundError
from app.schemas import ErrorDetail, ErrorResponse


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        message = "; ".join(str(err.get("msg", "")) for err in exc.errors()) or "invalid request"
        body = ErrorResponse(error=ErrorDetail(code="invalid_request", message=message))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=body.model_dump(),
        )

    @app.exception_handler(JobNotFoundError)
    async def handle_job_not_found(request: Request, exc: JobNotFoundError) -> JSONResponse:
        body = ErrorResponse(error=ErrorDetail(code="job_not_found", message=str(exc)))
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=body.model_dump(),
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        req_id = getattr(request.state, "req_id", None) or str(uuid.uuid4())
        body = ErrorResponse(
            error=ErrorDetail(code="internal_error", message="internal server error")
        )
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=body.model_dump(),
        )
        response.headers["X-Request-ID"] = req_id
        return response
