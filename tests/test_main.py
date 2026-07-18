# tests/test_main.py
import json
import logging

from fastapi.testclient import TestClient

from app.main import create_app


def test_app_skeleton_end_to_end(caplog):
    app = create_app()

    with TestClient(app) as client:
        assert app.state.ready is True

        assert client.get("/healthz").status_code == 200
        assert client.get("/readyz").status_code == 200

        with caplog.at_level(logging.INFO, logger="app.request"):
            client.get("/healthz")

        assert any(json.loads(r.getMessage())["route"] == "/healthz" for r in caplog.records)
