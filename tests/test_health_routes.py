from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.health import router as health_router


def _build_app(ready: bool) -> FastAPI:
    app = FastAPI()
    app.state.ready = ready
    app.include_router(health_router)
    return app


def test_healthz_returns_200_regardless_of_readiness():
    client = TestClient(_build_app(ready=False))
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_returns_200_when_ready():
    client = TestClient(_build_app(ready=True))
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readyz_returns_503_when_not_ready():
    client = TestClient(_build_app(ready=False))
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
