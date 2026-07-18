# app/main.py
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.errors import install_exception_handlers
from app.middleware import ObservabilityMiddleware
from app.observability.logging import configure_logging
from app.processor import MockProcessor
from app.queue import AsyncioJobQueue
from app.repository import InMemoryJobRepository
from app.routes.health import router as health_router
from app.routes.jobs import router as jobs_router
from app.routes.metrics import router as metrics_router
from app.service import JobService
from app.worker import run_worker


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logger = configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        stop_event = asyncio.Event()
        workers = [
            asyncio.create_task(
                run_worker(
                    app.state.job_queue, app.state.job_service, app.state.job_processor, stop_event
                )
            )
            for _ in range(settings.worker_pool_size)
        ]
        app.state.ready = True
        yield
        app.state.ready = False
        stop_event.set()
        try:
            await asyncio.wait_for(asyncio.gather(*workers), timeout=30)
        except TimeoutError:
            for worker in workers:
                worker.cancel()

    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings
    app.state.ready = False
    app.state.job_repository = InMemoryJobRepository()
    app.state.job_queue = AsyncioJobQueue()
    app.state.job_processor = MockProcessor(
        min_sleep_seconds=settings.mock_min_sleep_seconds,
        max_sleep_seconds=settings.mock_max_sleep_seconds,
        failure_rate=settings.mock_failure_rate,
    )
    app.state.job_service = JobService(
        repository=app.state.job_repository,
        queue=app.state.job_queue,
        max_attempts=settings.max_attempts,
    )
    install_exception_handlers(app)
    app.add_middleware(ObservabilityMiddleware, logger=logger)
    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(metrics_router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=app.state.settings.port)
