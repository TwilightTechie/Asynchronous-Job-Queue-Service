# tests/test_middleware.py
import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.middleware import ObservabilityMiddleware
from app.observability.logging import configure_logging


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.get("/dummy-mw-route")
    async def dummy() -> dict:
        return {"ok": True}

    logger = configure_logging("INFO")
    app.add_middleware(ObservabilityMiddleware, logger=logger)
    return app


def test_middleware_records_metrics_logs_and_sets_request_id(caplog):
    client = TestClient(_build_app())

    before = (
        REGISTRY.get_sample_value(
            "http_requests_total",
            {"method": "GET", "route": "/dummy-mw-route", "status": "200"},
        )
        or 0.0
    )

    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/dummy-mw-route")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    after = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": "GET", "route": "/dummy-mw-route", "status": "200"},
    )
    assert after == before + 1.0

    assert len(caplog.records) == 1
    payload = json.loads(caplog.records[0].getMessage())
    assert payload["route"] == "/dummy-mw-route"
    assert payload["status"] == 200
    assert payload["req_id"] == response.headers["X-Request-ID"]
    assert payload["dur_ms"] >= 0
