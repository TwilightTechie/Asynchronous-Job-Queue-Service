from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.observability.metrics import record_request
from app.queue import AsyncioJobQueue
from app.routes.metrics import router as metrics_router


def test_metrics_endpoint_exposes_prometheus_text():
    record_request("GET", "/test-metrics-route", 200, 0.01)

    app = FastAPI()
    app.state.job_queue = AsyncioJobQueue()
    app.include_router(metrics_router)
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert (
        'http_requests_total{method="GET",route="/test-metrics-route",status="200"}'
        in response.text
    )
    assert "job_queue_depth 0.0" in response.text
