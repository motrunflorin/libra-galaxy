"""Per-request correlation state.

``request_id`` travels from the HTTP edge through the orchestrator, agents,
tools and services into logs and audit records, so one identifier links the
whole chain (see ``docs/ARCHITECTURE.md`` — Observability).

Only identifiers live here. Never store banking payloads or credentials in
context variables: they would leak into every log line.
"""

from __future__ import annotations

from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar("libra_request_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("libra_user_id", default=None)


def set_request_id(value: str | None) -> None:
    _request_id.set(value)


def get_request_id() -> str | None:
    return _request_id.get()


def set_user_id(value: str | None) -> None:
    _user_id.set(value)


def get_user_id() -> str | None:
    return _user_id.get()


def snapshot() -> dict[str, str]:
    """Correlation fields to attach to a log record or telemetry entry."""
    data: dict[str, str] = {}
    request_id = get_request_id()
    user_id = get_user_id()
    if request_id:
        data["request_id"] = request_id
    if user_id:
        data["user_id"] = user_id
    return data
