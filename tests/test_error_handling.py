import json
import logging

from fastapi.testclient import TestClient

from app.main import create_app


def test_unhandled_exception_returns_structured_500_with_correlated_request_id(caplog):
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    app.state.job_service.submit_job = _boom

    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.post("/jobs", json={"type": "report", "input": {}})

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"

    assert "X-Request-ID" in response.headers
    log_payloads = [json.loads(r.getMessage()) for r in caplog.records]
    matching = [p for p in log_payloads if p["status"] == 500]
    assert len(matching) == 1
    assert matching[0]["req_id"] == response.headers["X-Request-ID"]
