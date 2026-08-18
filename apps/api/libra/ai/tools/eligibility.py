"""Tool eligibility: the enforcement point between an agent and the bank.

Eligibility is decided *before* execution from four independent conditions:

1. the tool must allow the selected agent;
2. the principal must hold every required permission;
3. the tool's risk must not exceed the risk ceiling for the request;
4. a tool that requires confirmation only runs once the user has confirmed.

A prompt cannot influence any of these. Rejections carry a reason so the
orchestrator can log why a capability was withheld.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from libra.ai.tools.contract import RiskLevel, ToolContext, ToolDefinition


AGENT_NOT_ALLOWED = "agent_not_allowed"
MISSING_PERMISSION = "missing_permission"
RISK_CEILING_EXCEEDED = "risk_ceiling_exceeded"
CONFIRMATION_REQUIRED = "confirmation_required"


@dataclass(frozen=True)
class EligibilityDecision:
    tool_name: str
    allowed: bool
    reason: str = ""

    @classmethod
    def allow(cls, tool_name: str) -> EligibilityDecision:
        return cls(tool_name=tool_name, allowed=True)

    @classmethod
    def deny(cls, tool_name: str, reason: str) -> EligibilityDecision:
        return cls(tool_name=tool_name, allowed=False, reason=reason)


def evaluate(
    definition: ToolDefinition,
    *,
    agent_id: str,
    context: ToolContext,
    risk_ceiling: RiskLevel = RiskLevel.HIGH,
) -> EligibilityDecision:
    """Decide whether one tool may run in this context."""
    if agent_id not in definition.allowed_agents:
        return EligibilityDecision.deny(definition.name, AGENT_NOT_ALLOWED)

    missing = definition.required_permissions - context.principal.permissions
    if missing:
        return EligibilityDecision.deny(definition.name, MISSING_PERMISSION)

    if definition.risk_level.rank > risk_ceiling.rank:
        return EligibilityDecision.deny(definition.name, RISK_CEILING_EXCEEDED)

    if definition.requires_confirmation and not context.user_confirmed:
        return EligibilityDecision.deny(definition.name, CONFIRMATION_REQUIRED)

    return EligibilityDecision.allow(definition.name)


def filter_eligible(
    definitions: Sequence[ToolDefinition],
    *,
    agent_id: str,
    context: ToolContext,
    risk_ceiling: RiskLevel = RiskLevel.HIGH,
) -> tuple[list[ToolDefinition], list[EligibilityDecision]]:
    """Split a tool list into (eligible tools, denial decisions)."""
    eligible: list[ToolDefinition] = []
    denials: list[EligibilityDecision] = []

    for definition in definitions:
        decision = evaluate(
            definition, agent_id=agent_id, context=context, risk_ceiling=risk_ceiling
        )
        if decision.allowed:
            eligible.append(definition)
        else:
            denials.append(decision)

    return eligible, denials
