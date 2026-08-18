"""Agent routing.

Deterministic: one intent maps to one agent. A model is not asked to choose a
specialist when a lookup table answers correctly, and the mapping is data, so
it can be reviewed and tested.

``UNKNOWN`` deliberately routes to the Document Intelligence agent — the only
agent that must cite a source for everything it says, which is the safest
default for an unclassified question.
"""

from __future__ import annotations

from dataclasses import dataclass

from libra.ai.orchestration.models import Intent

_INTENT_AGENT: dict[Intent, str] = {
    Intent.ACCOUNT_OVERVIEW: "financial_advisor",
    Intent.SPENDING_ANALYSIS: "transaction_intelligence",
    Intent.SUBSCRIPTION_REVIEW: "transaction_intelligence",
    Intent.WHAT_IF_SIMULATION: "financial_advisor",
    Intent.FINANCIAL_ADVICE: "financial_advisor",
    Intent.DOCUMENT_QUESTION: "document_intelligence",
    Intent.KNOWLEDGE_QUESTION: "document_intelligence",
    Intent.KYC_WORKFLOW: "compliance_kyc",
    # Payments are prepared by a deterministic flow and only then explained;
    # no agent may execute one.
    Intent.PAYMENT_ACTION: "financial_advisor",
    Intent.UNKNOWN: "document_intelligence",
}


@dataclass(frozen=True)
class RoutingDecision:
    agent_id: str
    reason: str
    deterministic: bool = True


class AgentRouter:
    def route(self, intent: Intent) -> RoutingDecision:
        agent_id = _INTENT_AGENT.get(intent, "document_intelligence")
        return RoutingDecision(
            agent_id=agent_id,
            reason=f"deterministic route for intent={intent.value}",
        )
