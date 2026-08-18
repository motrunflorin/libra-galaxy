"""Transaction domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from libra.core.money import Money


class Direction(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    user_id: str
    account_id: str
    booked_at: datetime
    #: Always a positive amount; ``direction`` carries the sign.
    amount: Money
    direction: Direction
    #: Raw descriptor exactly as received from the payment scheme.
    merchant_raw: str
    #: Normalized merchant identifier ("NETFLIX.COM" -> "netflix").
    merchant_key: str = ""
    #: Stable category identifier; the UI translates it.
    category_id: str = "uncategorized"
    #: Set when Transaction Intelligence proposed the category. Reviewable.
    category_source: str = "rule"

    @property
    def signed_amount(self) -> Money:
        return -self.amount if self.direction is Direction.DEBIT else self.amount


@dataclass(frozen=True)
class CategorySpending:
    category_id: str
    total: Money
    transaction_count: int


@dataclass(frozen=True)
class SpendingSummary:
    """Deterministic aggregation. The AI explains it; it never computes it."""

    currency: str
    period_start: datetime
    period_end: datetime
    total_spent: Money
    total_received: Money
    transaction_count: int
    by_category: tuple[CategorySpending, ...]

    @property
    def net(self) -> Money:
        return self.total_received - self.total_spent
