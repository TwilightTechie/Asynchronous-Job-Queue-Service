import json
import logging

from app.observability.logging import configure_logging, log_request


def test_log_request_emits_one_json_line_with_expected_keys(caplog):
    logger = configure_logging("INFO")

    with caplog.at_level(logging.INFO, logger="app.request"):
        log_request(
            logger,
            ts="2026-07-18T00:00:00+00:00",
            req_id="test-req-id",
            route="/healthz",
            status_code=200,
            dur_ms=12.34,
        )

    assert len(caplog.records) == 1
    payload = json.loads(caplog.records[0].getMessage())
    assert payload == {
        "ts": "2026-07-18T00:00:00+00:00",
        "req_id": "test-req-id",
        "route": "/healthz",
        "status": 200,
        "dur_ms": 12.34,
    }
