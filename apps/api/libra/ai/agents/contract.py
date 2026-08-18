"""Agent contract.

An agent is a bounded specialist. It receives an assembled context, may call
only the tools its specification allows, and returns a structured response.
It never queries the database, never calls another agent, and never decides
its own permissions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from libra.ai.context.models import AssembledContext
from libra.ai.tools.contract import RiskLevel, ToolContext, ToolOutcome
from libra.core.locale import Locale


@dataclass(frozen=True)
class AgentSpec:
    """The declared contract of one agent."""

    agent_id: str
    display_name: str
    purpose: str
    responsibilities: tuple[str, ...]
    #: Explicit anti-scope. Enforced by tool eligibility, stated for reviewers.
    prohibited: tuple[str, ...]
    allowed_tools: frozenset[str]
    #: Highest tool risk this agent may ever reach.
    risk_ceiling: RiskLevel = RiskLevel.LOW
    #: Identifies the prompt revision used, recorded in every agent run.
    prompt_version: str = "v0"
    #: How this agent is evaluated before release (see docs/AGENTS.md).
    evaluation: tuple[str, ...] = ()
    #: Planned capabilities, kept here so scope creep is visible in review.
    future_extensions: tuple[str, ...] = ()

    def allows_tool(self, tool_name: str) -> bool:
        return tool_name in self.allowed_tools


@dataclass(frozen=True)
class AgentRequest:
    """Everything an agent needs for one turn."""

    message: str
    context: AssembledContext
    tool_context: ToolContext
    locale: Locale
    #: Results of tools the orchestrator ran before invoking the agent.
    prior_outcomes: tuple[ToolOutcome, ...] = ()


@dataclass(frozen=True)
class AgentResponse:
    """A structured answer. ``text`` is the only part shown to the user."""

    agent_id: str
    text: str
    #: Identifiers of the context sections and tool outputs the answer used.
    citations: tuple[str, ...] = ()
    #: Machine-readable payload for the UI (charts, projections, drafts).
    data: dict[str, Any] = field(default_factory=dict)
    tool_outcomes: tuple[ToolOutcome, ...] = ()
    prompt_version: str = "v0"
    #: Set when the agent prepared an operation the user must confirm.
    pending_confirmation: dict[str, Any] | None = None


@runtime_checkable
class Agent(Protocol):
    spec: AgentSpec

    async def handle(self, request: AgentRequest) -> AgentResponse: ...
