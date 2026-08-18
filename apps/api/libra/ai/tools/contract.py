"""Tool contract.

A tool is the *only* bridge between an agent and application functionality.
Every tool declares, as data, what it is allowed to do — which agents may call
it, which permissions the caller needs, whether it changes state, how risky it
is and whether the user must confirm. Those declarations are enforced by
:mod:`libra.ai.tools.eligibility` before execution, not by prompt text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable

from pydantic import BaseModel

from libra.core.locale import DEFAULT_LOCALE, Locale
from libra.core.security.principal import Permission, Principal


class RiskLevel(str, Enum):
    """How much damage a wrong call could do."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def rank(self) -> int:
        return {"low": 0, "medium": 1, "high": 2}[self.value]


class SideEffect(str, Enum):
    #: Reads authoritative state. Safe to run concurrently.
    READ_ONLY = "read_only"
    #: Pure computation on inputs (scenario projections). Safe to run concurrently.
    COMPUTE = "compute"
    #: Creates a draft/intent that still requires a deterministic execution step.
    PREPARES_MUTATION = "prepares_mutation"
    #: Changes authoritative state. Never speculative, never parallel.
    MUTATES = "mutates"

    @property
    def is_safe_to_parallelize(self) -> bool:
        return self in (SideEffect.READ_ONLY, SideEffect.COMPUTE)


@dataclass(frozen=True)
class ToolContext:
    """Everything a tool may know about the caller.

    The principal is passed through unchanged so the underlying service applies
    the same authorization it would apply to an HTTP request.
    """

    principal: Principal
    request_id: str
    locale: Locale = DEFAULT_LOCALE
    conversation_id: str | None = None
    #: Set when the user explicitly confirmed the pending operation.
    user_confirmed: bool = False
    #: Deduplicates mutations retried by the orchestrator.
    idempotency_key: str | None = None


ToolCallable = Callable[[ToolContext, BaseModel], Awaitable[BaseModel]]


@dataclass(frozen=True)
class ToolDefinition:
    """Registry entry for one tool."""

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: ToolCallable
    #: Agent ids allowed to call this tool. Empty means "no agent" (admin only).
    allowed_agents: frozenset[str] = frozenset()
    required_permissions: frozenset[Permission] = frozenset()
    side_effect: SideEffect = SideEffect.READ_ONLY
    risk_level: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    timeout_seconds: float | None = None
    #: Free-form tags used for grouping in the admin dashboard.
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.side_effect is SideEffect.MUTATES and not self.requires_confirmation:
            raise ValueError(
                f"Tool {self.name!r} mutates state and must require confirmation."
            )

    @property
    def is_parallel_safe(self) -> bool:
        return self.side_effect.is_safe_to_parallelize

    def public_metadata(self) -> dict[str, Any]:
        """Safe to expose in the admin dashboard and in agent prompts."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
            "output_schema": self.output_model.model_json_schema(),
            "allowed_agents": sorted(self.allowed_agents),
            "required_permissions": sorted(item.value for item in self.required_permissions),
            "side_effect": self.side_effect.value,
            "risk_level": self.risk_level.value,
            "requires_confirmation": self.requires_confirmation,
            "parallel_safe": self.is_parallel_safe,
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class ToolCall:
    """A request to execute one tool, with an auditable selection reason."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    #: Why this tool was chosen. Written to telemetry, never invented later.
    reason: str = ""


@dataclass(frozen=True)
class ToolOutcome:
    """The recorded result of one tool execution."""

    tool_name: str
    success: bool
    duration_ms: float
    reason: str
    output: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
