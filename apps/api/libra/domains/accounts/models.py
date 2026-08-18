"""Account domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from libra.core.money import Money


class AccountType(str, Enum):
    CURRENT = "current"
    SAVINGS = "savings"
    CARD = "card"


class AccountStatus(str, Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class SubaccountPurpose(str, Enum):
    """Stable identifiers; display names come from the translation files."""

    EMERGENCY_FUND = "emergency_fund"
    VACATION = "vacation"
    BILLS = "bills"
    INVESTMENTS = "investments"
    PERSONAL_GOAL = "personal_goal"


@dataclass(frozen=True)
class Account:
    account_id: str
    user_id: str
    iban: str
    #: Stable identifier; the UI shows a translated label for the type.
    account_type: AccountType
    currency: str
    balance: Money
    available_balance: Money
    status: AccountStatus = AccountStatus.ACTIVE
    #: User-chosen label. Never translated.
    label: str = ""
    opened_at: datetime | None = None


@dataclass(frozen=True)
class Subaccount:
    subaccount_id: str
    user_id: str
    account_id: str
    purpose: SubaccountPurpose
    balance: Money
    label: str = ""
