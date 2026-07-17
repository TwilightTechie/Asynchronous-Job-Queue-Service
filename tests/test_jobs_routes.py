from fastapi.testclient import TestClient

from app.main import create_app


def test_post_jobs_returns_201_with_id_status_created_at():
    client = TestClient(create_app())

    response = client.post("/jobs", json={"type": "report", "input": {"customer_id": "abc123"}})

    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"id", "status", "created_at"}
    assert body["status"] == "queued"


def test_post_jobs_does_not_wait_on_processing():
    client = TestClient(create_app())

    response = client.post("/jobs", json={"type": "transcode", "input": {}})

    assert response.status_code == 201


def test_post_jobs_invalid_type_returns_structured_422():
    client = TestClient(create_app())

    response = client.post("/jobs", json={"type": "not-a-real-type", "input": {}})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_request"
    assert "message" in body["error"]


def test_post_jobs_missing_input_returns_structured_422():
    client = TestClient(create_app())

    response = client.post("/jobs", json={"type": "report"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
