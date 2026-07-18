import time

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _poll_until_terminal(client: TestClient, job_id: str, attempts: int = 100) -> dict:
    for _ in range(attempts):
        body = client.get(f"/jobs/{job_id}").json()
        if body["status"] in ("completed", "failed"):
            return body
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} did not reach a terminal state in time")


def test_job_lifecycle_completes_end_to_end_via_http():
    settings = Settings(
        mock_min_sleep_seconds=0.01,
        mock_max_sleep_seconds=0.02,
        mock_failure_rate=0.0,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        create_response = client.post(
            "/jobs", json={"type": "report", "input": {"customer_id": "abc123"}}
        )
        assert create_response.status_code == 201
        job_id = create_response.json()["id"]
        assert create_response.json()["status"] == "queued"

        body = _poll_until_terminal(client, job_id)

        assert body["status"] == "completed"
        assert body["result"] is not None
        assert body["error"] is None
        assert body["attempts"] == 1


def test_job_lifecycle_fails_after_exhausting_retries_via_http():
    settings = Settings(
        mock_min_sleep_seconds=0.01,
        mock_max_sleep_seconds=0.02,
        mock_failure_rate=1.0,
        max_attempts=2,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        create_response = client.post("/jobs", json={"type": "export", "input": {}})
        job_id = create_response.json()["id"]

        body = _poll_until_terminal(client, job_id)

        assert body["status"] == "failed"
        assert body["result"] is None
        assert body["error"] is not None
        assert body["attempts"] == 2
