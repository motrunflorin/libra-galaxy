"""Orchestration request, trace and result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from libra.ai.conversations.models import Channel
from libra.ai.tools.contract import RiskLevel, ToolOutcome
from libra.core.locale import Locale
from libra.core.security.principal import Principal


class Intent(str, Enum):
    """Deterministically classified request intent.

    Coarse on purpose: intents map to agents, not to individual features.
    """

    ACCOUNT_OVERVIEW = "account_overview"
    SPENDING_ANALYSIS = "spending_analysis"
    SUBSCRIPTION_REVIEW = "subscription_review"
    WHAT_IF_SIMULATION = "what_if_simulation"
    FINANCIAL_ADVICE = "financial_advice"
    DOCUMENT_QUESTION = "document_question"
    KNOWLEDGE_QUESTION = "knowledge_question"
    PAYMENT_ACTION = "payment_action"
    KYC_WORKFLOW = "kyc_workflow"
    #: Nothing matched with sufficient confidence.
    UNKNOWN = "unknown"


class Stage(str, Enum):
    """The fixed orchestration pipeline. Every stage is recorded."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    INTENT = "intent"
    RISK = "risk"
    CONTEXT = "context"
    AGENT_SELECTION = "agent_selection"
    TOOL_ELIGIBILITY = "tool_eligibility"
    EXECUTION = "execution"
    VALIDATION = "validation"
    RESPONSE = "response"
    TELEMETRY = "telemetry"


@dataclass(frozen=True)
class TraceEntry:
    """One recorded stage outcome.

    Traces are internal: they go to logs and to the admin dashboard, never to
    a banking user's response.
    """

    stage: Stage
    detail: str
    duration_ms: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OrchestrationRequest:
    principal: Principal
    message: str
    conversation_id: str | None = None
    locale: Locale = Locale.RO
    channel: Channel = Channel.TEXT
    #: True when the user has confirmed a previously prepared operation.
    user_confirmed: bool = False
    request_id: str = ""


@dataclass(frozen=True)
class OrchestrationResult:
    """What the API returns, plus what only telemetry sees."""

    text: str
    agent_id: str
    intent: Intent
    risk: RiskLevel
    conversation_id: str | None = None
    citations: tuple[str, ...] = ()
    data: dict[str, Any] = field(default_factory=dict)
    tool_outcomes: tuple[ToolOutcome, ...] = ()
    #: Internal only — never serialised into a customer-facing response.
    trace: tuple[TraceEntry, ...] = ()
    pending_confirmation: dict[str, Any] | None = None
