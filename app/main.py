# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.routes.health import router as health_router


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
    app.include_router(health_router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=app.state.settings.port)
