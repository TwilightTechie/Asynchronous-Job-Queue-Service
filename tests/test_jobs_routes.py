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


def test_get_job_returns_full_job_state():
    client = TestClient(create_app())
    created = client.post("/jobs", json={"type": "report", "input": {"a": 1}}).json()

    response = client.get(f"/jobs/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["type"] == "report"
    assert body["input"] == {"a": 1}
    assert body["status"] == "queued"
    assert body["attempts"] == 0
    assert "max_attempts" in body
    assert "created_at" in body
    assert "updated_at" in body


def test_get_job_unknown_id_returns_structured_404():
    client = TestClient(create_app())

    response = client.get("/jobs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "job_not_found"


def test_list_jobs_returns_all_jobs():
    client = TestClient(create_app())
    client.post("/jobs", json={"type": "report", "input": {}})
    client.post("/jobs", json={"type": "export", "input": {}})

    response = client.get("/jobs")

    assert response.status_code == 200
    body = response.json()
    assert len(body["jobs"]) == 2


def test_list_jobs_filters_by_status():
    client = TestClient(create_app())
    client.post("/jobs", json={"type": "report", "input": {}})

    response = client.get("/jobs", params={"status": "queued"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["status"] == "queued"


def test_list_jobs_invalid_status_returns_structured_422():
    client = TestClient(create_app())

    response = client.get("/jobs", params={"status": "not-a-real-status"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
