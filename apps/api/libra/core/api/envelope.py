"""The single response contract used by every endpoint.

Success::

    {"success": true, "message": "...", "body": {...}, "request_id": "req_..."}

Failure::

    {"success": false,
     "error": {"code": "...", "message": "...", "details": null},
     "request_id": "req_..."}

The envelope never replaces HTTP status codes: a 404 still returns 404.
"""

from __future__ import annotations

from typing import Any

from libra.core.errors import ErrorCode
from libra.core.request_context import get_request_id


def success(body: dict[str, Any] | None = None, message: str = "OK") -> dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "body": body or {},
        "request_id": get_request_id(),
    }


def failure(
    code: ErrorCode | str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "error": {
            "code": code.value if isinstance(code, ErrorCode) else str(code),
            "message": message,
            "details": details,
        },
        "request_id": get_request_id(),
    }
