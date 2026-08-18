"""Structured logging with correlation identifiers and redaction.

Adapted from the reference project's JSONL logger, with two banking-driven
changes:

1. every record automatically carries ``request_id``/``user_id`` from
   :mod:`libra.core.request_context`, so a failure can be traced across
   frontend -> API -> orchestrator -> agent -> tool -> service -> database;
2. a redaction filter drops known-sensitive keys before anything is written.

Log *events*, not payloads: identifiers, counts, durations and outcomes.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from libra.core.config import ObservabilitySettings
from libra.core.request_context import snapshot

#: Keys that must never reach a log sink, whatever the caller passes.
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "new_password",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "authorization",
        "secret",
        "iban",
        "card_number",
        "cvv",
        "pin",
        "national_id",
        "document_image",
        "content",
        "message",
        "answer",
        "prompt",
    }
)

REDACTED = "[redacted]"


def redact(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively replace sensitive values with ``[redacted]``."""
    clean: dict[str, Any] = {}
    for key, value in data.items():
        if key.lower() in SENSITIVE_KEYS:
            clean[key] = REDACTED
        elif isinstance(value, dict):
            clean[key] = redact(value)
        elif isinstance(value, list):
            clean[key] = [redact(item) if isinstance(item, dict) else item for item in value]
        else:
            clean[key] = value
    return clean


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with correlation fields merged in."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        payload.update(snapshot())

        event_data = getattr(record, "event_data", None)
        if isinstance(event_data, dict):
            payload.update(redact(event_data))

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(settings: ObservabilitySettings) -> None:
    """Install the configured handler once, replacing prior handlers."""
    root = logging.getLogger()
    root.setLevel(settings.log_level)

    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler()
    if settings.log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
    root.addHandler(handler)


def log_event(
    logger: logging.Logger, event: str, /, level: int = logging.INFO, **fields: Any
) -> None:
    """Emit a structured event: ``log_event(LOGGER, "tool.executed", tool=...)``."""
    logger.log(level, event, extra={"event_data": fields})
