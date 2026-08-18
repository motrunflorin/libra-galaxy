"""Telemetry records.

Adapted from the reference project's per-turn metric, with the content
removed. That implementation stored the full question and answer in its
metrics table; in a bank those strings are customer financial data and must
not be duplicated into an observability store. Records here keep identifiers,
counts, durations and outcomes — enough to debug and to bill, not enough to
leak.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ToolInvocationRecord:
    run_id: str
    tool_name: str
    success: bool
    duration_ms: float
    #: Why the tool was selected. Audit trail for capability use.
    reason: str = ""
    error_code: str | None = None


@dataclass(frozen=True)
class UsageRecord:
    """Token usage and estimated cost for one model call."""

    run_id: str
    deployment: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    estimated_cost_usd: float = 0.0
    #: Attribution dimensions for the cost dashboard.
    feature: str = "assistant"
    agent_id: str = ""
    environment: str = "local"
    occurred_at: datetime = field(default_factory=_now)


@dataclass(frozen=True)
class AgentRunRecord:
    """One orchestrated turn, end to end."""

    run_id: str
    request_id: str
    user_id: str
    conversation_id: str | None
    agent_id: str
    intent: str
    risk_level: str
    prompt_version: str
    #: Chat deployment used, from configuration.
    deployment: str = ""
    latency_ms: float = 0.0
    success: bool = True
    error_code: str | None = None
    tool_count: int = 0
    retrieved_chunks: int = 0
    context_chars: int = 0
    #: Stage names in execution order; no message content.
    stages: tuple[str, ...] = ()
    started_at: datetime = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "agent_id": self.agent_id,
            "intent": self.intent,
            "risk_level": self.risk_level,
            "prompt_version": self.prompt_version,
            "deployment": self.deployment,
            "latency_ms": round(self.latency_ms, 2),
            "success": self.success,
            "error_code": self.error_code,
            "tool_count": self.tool_count,
            "retrieved_chunks": self.retrieved_chunks,
            "context_chars": self.context_chars,
            "stages": list(self.stages),
            "started_at": self.started_at.isoformat(),
        }
