import pytest
from pydantic import ValidationError

from app.schemas import ErrorDetail, ErrorResponse, JobCreateRequest


def test_job_create_request_accepts_valid_payload():
    req = JobCreateRequest(type="report", input={"customer_id": "abc123"})
    assert req.type == "report"
    assert req.input == {"customer_id": "abc123"}


def test_job_create_request_rejects_invalid_type():
    with pytest.raises(ValidationError):
        JobCreateRequest(type="not-a-real-type", input={})


def test_job_create_request_requires_input():
    with pytest.raises(ValidationError):
        JobCreateRequest(type="report")


def test_error_response_shape():
    err = ErrorResponse(error=ErrorDetail(code="invalid_request", message="bad payload"))
    assert err.model_dump() == {"error": {"code": "invalid_request", "message": "bad payload"}}
