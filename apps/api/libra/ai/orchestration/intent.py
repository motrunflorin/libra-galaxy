"""Deterministic intent classification.

Obvious intents are matched by rules in both Romanian and English: it is
cheaper, reproducible, testable and adds no model latency. Model-based
classification is a later addition for the ``UNKNOWN`` bucket only — the point
where it would actually add value.

Phrase tables live here as data so they can be extended and unit-tested
without touching the orchestrator.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from libra.ai.orchestration.models import Intent

#: intent -> trigger phrases. Romanian entries are matched without diacritics,
#: because customers type both "cheltuit" and "cheltuiț".
_PHRASES: dict[Intent, tuple[str, ...]] = {
    Intent.ACCOUNT_OVERVIEW: (
        "balance", "my accounts", "how much do i have", "account overview",
        "sold", "soldul", "conturile mele", "cat am in cont", "ce bani am",
    ),
    Intent.SPENDING_ANALYSIS: (
        "how much did i spend", "spending", "expenses", "where did my money go",
        "cat am cheltuit", "cheltuieli", "pe ce am dat banii",
    ),
    Intent.SUBSCRIPTION_REVIEW: (
        "subscription", "subscriptions", "recurring payment", "cancel netflix",
        "abonament", "abonamente", "plati recurente",
    ),
    Intent.WHAT_IF_SIMULATION: (
        "what if", "what happens if", "simulate", "scenario", "cashplay",
        "ce se intampla daca", "daca economisesc", "simuleaza", "scenariu",
    ),
    Intent.FINANCIAL_ADVICE: (
        "should i", "financial health", "savings goal", "budget", "advice",
        "sanatate financiara", "obiectiv de economii", "buget", "sfat",
    ),
    Intent.DOCUMENT_QUESTION: (
        "statement", "my document", "uploaded file", "this pdf", "invoice",
        "extras de cont", "documentul meu", "factura",
    ),
    Intent.KNOWLEDGE_QUESTION: (
        "how do i", "what is", "policy", "procedure", "fee", "terms",
        "cum pot", "ce inseamna", "politica", "procedura", "comision",
    ),
    Intent.PAYMENT_ACTION: (
        "send money", "transfer", "pay ", "make a payment", "split the bill",
        "trimite bani", "transfer catre", "plateste", "imparte nota",
    ),
    Intent.KYC_WORKFLOW: (
        "identity verification", "kyc", "verify my identity", "id document",
        "verificare identitate", "act de identitate",
    ),
}

#: Checked in order, so a payment request is not swallowed by a broader match.
_PRIORITY: tuple[Intent, ...] = (
    Intent.PAYMENT_ACTION,
    Intent.KYC_WORKFLOW,
    Intent.WHAT_IF_SIMULATION,
    Intent.SUBSCRIPTION_REVIEW,
    Intent.SPENDING_ANALYSIS,
    Intent.ACCOUNT_OVERVIEW,
    Intent.DOCUMENT_QUESTION,
    Intent.FINANCIAL_ADVICE,
    Intent.KNOWLEDGE_QUESTION,
)


def normalize(text: str) -> str:
    """Casefold and strip diacritics so RO input matches reliably."""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


@dataclass(frozen=True)
class IntentDecision:
    intent: Intent
    #: The phrase that matched, recorded so routing is explainable.
    matched_phrase: str = ""
    deterministic: bool = True

    @property
    def is_known(self) -> bool:
        return self.intent is not Intent.UNKNOWN


class IntentClassifier:
    def classify(self, message: str) -> IntentDecision:
        text = normalize(message)
        if not text.strip():
            return IntentDecision(Intent.UNKNOWN)

        for intent in _PRIORITY:
            for phrase in _PHRASES[intent]:
                if normalize(phrase) in text:
                    return IntentDecision(intent=intent, matched_phrase=phrase)

        return IntentDecision(Intent.UNKNOWN)
