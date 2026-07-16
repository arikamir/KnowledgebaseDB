"""Structured logging helpers."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


SAFE_TELEMETRY_FIELDS = (
    "trace_id",
    "route_class",
    "duration_ms",
    "outcome",
    "dependency_outcome",
    "status_code",
    "actor_type",
    "denial_code",
)


class JsonFormatter(logging.Formatter):
    """Render log records as a compact JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in SAFE_TELEMETRY_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
