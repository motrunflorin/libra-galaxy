"""Application error hierarchy and stable machine-readable error codes.

Every failure that reaches the API is translated into one ``LibraError``
subclass carrying a stable ``ErrorCode`` and an HTTP status. Error codes are
part of the public API contract (see ``docs/API_CONVENTIONS.md``) and must not
be renamed without a versioning decision.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Stable, machine-readable error codes returned to clients."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_INVALID = "AUTH_INVALID"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    CONFLICT = "CONFLICT"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"

    PERSISTENCE_ERROR = "PERSISTENCE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"

    AI_PROVIDER_ERROR = "AI_PROVIDER_ERROR"
    AI_PROVIDER_UNAVAILABLE = "AI_PROVIDER_UNAVAILABLE"
    AGENT_NOT_AVAILABLE = "AGENT_NOT_AVAILABLE"
    AGENT_EXECUTION_ERROR = "AGENT_EXECUTION_ERROR"
    TOOL_NOT_ELIGIBLE = "TOOL_NOT_ELIGIBLE"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
    RETRIEVAL_ERROR = "RETRIEVAL_ERROR"
    VOICE_SERVICE_ERROR = "VOICE_SERVICE_ERROR"

    INTERNAL_ERROR = "INTERNAL_ERROR"


class LibraError(Exception):
    """Base class for all expected application failures."""

    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    status_code: int = 500
    #: Safe to show to an end user. Internal errors deliberately say nothing.
    default_message = "The request could not be completed."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.details = details


class ValidationError(LibraError):
    code = ErrorCode.VALIDATION_ERROR
    status_code = 422
    default_message = "The submitted data is invalid."


class AuthenticationRequiredError(LibraError):
    code = ErrorCode.AUTH_REQUIRED
    status_code = 401
    default_message = "Authentication is required."


class InvalidCredentialsError(LibraError):
    code = ErrorCode.AUTH_INVALID
    status_code = 401
    default_message = "The provided credentials are not valid."


class PermissionDeniedError(LibraError):
    code = ErrorCode.PERMISSION_DENIED
    status_code = 403
    default_message = "You are not allowed to perform this operation."


class ResourceNotFoundError(LibraError):
    code = ErrorCode.RESOURCE_NOT_FOUND
    status_code = 404
    default_message = "The requested resource was not found."


class ConflictError(LibraError):
    code = ErrorCode.CONFLICT
    status_code = 409
    default_message = "The operation conflicts with the current state."


class ConfirmationRequiredError(LibraError):
    code = ErrorCode.CONFIRMATION_REQUIRED
    status_code = 409
    default_message = "Explicit user confirmation is required."


class ConfigurationError(LibraError):
    code = ErrorCode.CONFIGURATION_ERROR
    status_code = 500
    default_message = "The service is not configured correctly."


class PersistenceError(LibraError):
    code = ErrorCode.PERSISTENCE_ERROR
    status_code = 503
    default_message = "A storage operation failed."


class AIProviderError(LibraError):
    code = ErrorCode.AI_PROVIDER_ERROR
    status_code = 502
    default_message = "The AI provider returned an error."


class AIProviderUnavailableError(LibraError):
    """Microsoft Foundry is unreachable or unconfigured.

    Libra Galaxy has no automatic provider fallback: the request fails cleanly
    and observably instead of silently switching provider.
    """

    code = ErrorCode.AI_PROVIDER_UNAVAILABLE
    status_code = 503
    default_message = "The AI service is currently unavailable."


class AgentNotAvailableError(LibraError):
    code = ErrorCode.AGENT_NOT_AVAILABLE
    status_code = 503
    default_message = "No agent is available to handle this request."


class AgentExecutionError(LibraError):
    code = ErrorCode.AGENT_EXECUTION_ERROR
    status_code = 502
    default_message = "The agent could not complete the request."


class ToolNotEligibleError(LibraError):
    code = ErrorCode.TOOL_NOT_ELIGIBLE
    status_code = 403
    default_message = "The requested capability is not available in this context."


class ToolTimeoutError(LibraError):
    code = ErrorCode.TOOL_TIMEOUT
    status_code = 504
    default_message = "A capability took too long to respond."


class ToolExecutionError(LibraError):
    code = ErrorCode.TOOL_EXECUTION_ERROR
    status_code = 502
    default_message = "A capability failed to execute."


class RetrievalError(LibraError):
    code = ErrorCode.RETRIEVAL_ERROR
    status_code = 503
    default_message = "Knowledge retrieval failed."
