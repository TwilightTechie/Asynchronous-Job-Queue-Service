# app/middleware.py
import logging
import time
import uuid
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.observability.logging import log_request
from app.observability.metrics import record_request


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.req_id = req_id
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_seconds = time.perf_counter() - start
            route = request.scope.get("route")
            route_path = route.path if route is not None else request.url.path
            record_request(request.method, route_path, 500, duration_seconds)
            log_request(
                self.logger,
                ts=datetime.now(UTC).isoformat(),
                req_id=req_id,
                route=route_path,
                status_code=500,
                dur_ms=duration_seconds * 1000,
            )
            raise

        duration_seconds = time.perf_counter() - start
        route = request.scope.get("route")
        route_path = route.path if route is not None else request.url.path

        record_request(request.method, route_path, response.status_code, duration_seconds)
        log_request(
            self.logger,
            ts=datetime.now(UTC).isoformat(),
            req_id=req_id,
            route=route_path,
            status_code=response.status_code,
            dur_ms=duration_seconds * 1000,
        )

        response.headers["X-Request-ID"] = req_id
        return response
