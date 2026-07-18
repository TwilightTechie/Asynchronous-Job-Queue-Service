import json
import logging
import sys


def configure_logging(log_level: str) -> logging.Logger:
    logger = logging.getLogger("app.request")
    logger.setLevel(log_level)
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler(sys.stdout))
    return logger


def log_request(
    logger: logging.Logger,
    *,
    ts: str,
    req_id: str,
    route: str,
    status_code: int,
    dur_ms: float,
) -> None:
    logger.info(
        json.dumps(
            {
                "ts": ts,
                "req_id": req_id,
                "route": route,
                "status": status_code,
                "dur_ms": round(dur_ms, 2),
            }
        )
    )
