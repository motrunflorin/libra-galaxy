"""Scenario inputs and projected outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from libra.core.money import Money


class ChangeKind(str, Enum):
    #: Repeats every month from ``start_month`` (subscriptions, savings, rent).
    RECURRING = "recurring"
    #: Happens once in ``start_month`` (a purchase, a bonus).
    ONE_OFF = "one_off"


@dataclass(frozen=True)
class ScenarioChange:
    """One modification the user wants to simulate.

    ``amount`` is signed: negative reduces the monthly balance (a new
    subscription), positive increases it (a raise, a cancelled subscription).
    """

    change_id: str
    kind: ChangeKind
    amount: Money
    #: 1-based month in which the change first applies.
    start_month: int = 1
    #: ``None`` means "until the end of the horizon".
    end_month: int | None = None
    label: str = ""


@dataclass(frozen=True)
class ScenarioInput:
    """A complete, self-contained simulation request.

    The caller supplies the current financial state explicitly (obtained from
    AccountService/TransactionService), so the engine stays pure and testable.
    """

    opening_balance: Money
    monthly_income: Money
    monthly_expenses: Money
    horizon_months: int = 12
    changes: tuple[ScenarioChange, ...] = ()


@dataclass(frozen=True)
class MonthProjection:
    month: int
    income: Money
    expenses: Money
    change_delta: Money
    net: Money
    closing_balance: Money


@dataclass(frozen=True)
class ScenarioProjection:
    currency: str
    opening_balance: Money
    closing_balance: Money
    total_change_delta: Money
    #: First month (1-based) where the balance turns negative, if any.
    first_negative_month: int | None
    months: tuple[MonthProjection, ...] = field(default_factory=tuple)

    @property
    def horizon_months(self) -> int:
        return len(self.months)
