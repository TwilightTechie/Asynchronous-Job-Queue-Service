# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.errors import install_exception_handlers
from app.repository import InMemoryJobRepository
from app.routes.health import router as health_router
from app.routes.jobs import router as jobs_router
from app.service import JobService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.ready = True
        yield
        app.state.ready = False

    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings
    app.state.ready = False
    app.state.job_repository = InMemoryJobRepository()
    app.state.job_service = JobService(
        repository=app.state.job_repository, max_attempts=settings.max_attempts
    )
    install_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(jobs_router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=app.state.settings.port)
