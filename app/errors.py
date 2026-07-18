from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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
