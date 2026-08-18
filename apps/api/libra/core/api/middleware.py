"""Request correlation middleware."""

from __future__ import annotations

import time
import uuid
from typing import Any, Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from libra.core.logging import log_event
from libra.core.request_context import set_request_id, set_user_id

import logging

LOGGER = logging.getLogger("libra.request")

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request id, expose it, and log one structured access event.

    A client-supplied id is accepted so the frontend can correlate its own
    traces, but it is length-limited and never trusted as an identity.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")[:64].strip()
        request_id = incoming or f"req_{uuid.uuid4().hex[:16]}"
        set_request_id(request_id)
        set_user_id(None)
        request.state.request_id = request_id

        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            _log_access(request, status_code, (time.perf_counter() - started) * 1000)


def _log_access(request: Request, status_code: int, duration_ms: float) -> None:
    route: Any = request.scope.get("route")
    log_event(
        LOGGER,
        "http.request",
        method=request.method,
        # Log the route template, not the concrete path: concrete paths carry
        # resource identifiers.
        path=getattr(route, "path", request.url.path),
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
    )
