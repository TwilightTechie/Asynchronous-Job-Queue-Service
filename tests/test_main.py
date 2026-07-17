# tests/test_main.py
from fastapi.testclient import TestClient

from app.main import create_app


def test_app_skeleton_end_to_end():
    app = create_app()

    with TestClient(app) as client:
        assert app.state.ready is True

        healthz = client.get("/healthz")
        assert healthz.status_code == 200
        assert healthz.json() == {"status": "ok"}

        readyz = client.get("/readyz")
        assert readyz.status_code == 200
        assert readyz.json() == {"status": "ready"}
