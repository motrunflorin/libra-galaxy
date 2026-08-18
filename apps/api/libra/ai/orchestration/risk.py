"""Risk classification.

Risk is derived from the *intent*, not from the wording of the message: a
model-visible string can never lower the risk ceiling of a request. The
resulting ceiling caps which tools may run, on top of the agent's own ceiling.
"""

from __future__ import annotations

from dataclasses import dataclass

from libra.ai.orchestration.models import Intent
from libra.ai.tools.contract import RiskLevel

_INTENT_RISK: dict[Intent, RiskLevel] = {
    Intent.ACCOUNT_OVERVIEW: RiskLevel.LOW,
    Intent.SPENDING_ANALYSIS: RiskLevel.LOW,
    Intent.WHAT_IF_SIMULATION: RiskLevel.LOW,
    Intent.KNOWLEDGE_QUESTION: RiskLevel.LOW,
    Intent.DOCUMENT_QUESTION: RiskLevel.LOW,
    Intent.FINANCIAL_ADVICE: RiskLevel.LOW,
    Intent.SUBSCRIPTION_REVIEW: RiskLevel.MEDIUM,
    Intent.KYC_WORKFLOW: RiskLevel.MEDIUM,
    Intent.PAYMENT_ACTION: RiskLevel.HIGH,
    Intent.UNKNOWN: RiskLevel.LOW,
}


@dataclass(frozen=True)
class RiskAssessment:
    level: RiskLevel
    reason: str
    #: Highest tool risk permitted for this request.
    tool_ceiling: RiskLevel
    requires_confirmation: bool


class RiskClassifier:
    def assess(self, intent: Intent) -> RiskAssessment:
        level = _INTENT_RISK.get(intent, RiskLevel.LOW)
        return RiskAssessment(
            level=level,
            reason=f"intent={intent.value}",
            # An agent may never reach above the request's own risk level.
            tool_ceiling=level,
            requires_confirmation=level is RiskLevel.HIGH,
        )
