"""Translate exceptions into the failure envelope.

Only ``LibraError`` carries a user-safe message. Unexpected exceptions are
logged with their traceback and reported as a generic ``INTERNAL_ERROR`` so
stack traces, driver messages and identifiers never reach a client.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
# Starlette's HTTPException is the base class FastAPI's inherits from, so
# registering it here also covers framework-raised 404/405 responses.
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from libra.core.api.envelope import failure
from libra.core.errors import ErrorCode, LibraError

LOGGER = logging.getLogger("libra.errors")

#: HTTP statuses raised by the framework itself, mapped to stable codes.
_HTTP_STATUS_CODES = {
    401: ErrorCode.AUTH_REQUIRED,
    403: ErrorCode.PERMISSION_DENIED,
    404: ErrorCode.RESOURCE_NOT_FOUND,
    405: ErrorCode.VALIDATION_ERROR,
    409: ErrorCode.CONFLICT,
    429: ErrorCode.RATE_LIMITED,
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(LibraError)
    async def _libra_error(_: Request, error: LibraError) -> JSONResponse:
        LOGGER.warning(
            "application.error",
            extra={"event_data": {"code": error.code.value, "status": error.status_code}},
        )
        return JSONResponse(
            status_code=error.status_code,
            content=failure(error.code, error.message, error.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        fields = sorted(
            {".".join(str(part) for part in item["loc"][1:]) for item in error.errors()}
        )
        return JSONResponse(
            status_code=422,
            content=failure(
                ErrorCode.VALIDATION_ERROR,
                "The submitted data is invalid.",
                {"fields": fields},
            ),
        )

    @app.exception_handler(HTTPException)
    async def _http_error(_: Request, error: HTTPException) -> JSONResponse:
        code = _HTTP_STATUS_CODES.get(error.status_code, ErrorCode.INTERNAL_ERROR)
        message = error.detail if isinstance(error.detail, str) else "The request failed."
        return JSONResponse(status_code=error.status_code, content=failure(code, message))

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, error: Exception) -> JSONResponse:
        LOGGER.exception("unhandled.error", extra={"event_data": {"type": type(error).__name__}})
        return JSONResponse(
            status_code=500,
            content=failure(ErrorCode.INTERNAL_ERROR, "The request could not be completed."),
        )
