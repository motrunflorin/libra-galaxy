"""Transaction application service."""

from __future__ import annotations

from datetime import datetime

from libra.core.money import Money, sum_money
from libra.core.persistence.repository import Page
from libra.core.security.authorization import require_permission
from libra.core.security.principal import Permission, Principal
from libra.domains.transactions.models import (
    CategorySpending,
    Direction,
    SpendingSummary,
    Transaction,
)
from libra.domains.transactions.repository import TransactionRepository

MAX_PAGE_SIZE = 200


class TransactionService:
    def __init__(self, transactions: TransactionRepository) -> None:
        self._transactions = transactions

    async def list_transactions(
        self,
        principal: Principal,
        *,
        account_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Page[Transaction]:
        require_permission(principal, Permission.TRANSACTIONS_READ)
        safe_limit = max(1, min(int(limit), MAX_PAGE_SIZE))
        safe_offset = max(0, int(offset))

        items = await self._transactions.list_for_user(
            principal.user_id,
            account_id=account_id,
            since=since,
            until=until,
            limit=safe_limit,
            offset=safe_offset,
        )
        total = await self._transactions.count_for_user(
            principal.user_id, account_id=account_id, since=since, until=until
        )
        return Page(items=items, total=total, limit=safe_limit, offset=safe_offset)

    async def spending_summary(
        self,
        principal: Principal,
        *,
        since: datetime,
        until: datetime,
        currency: str,
        account_id: str | None = None,
    ) -> SpendingSummary:
        """Exact spending totals for a period.

        This is the answer to "how much did I spend last week?". Retrieval,
        memory and model output are never used for these numbers.
        """
        require_permission(principal, Permission.TRANSACTIONS_READ)

        transactions = await self._transactions.list_for_user(
            principal.user_id,
            account_id=account_id,
            since=since,
            until=until,
            limit=MAX_PAGE_SIZE * 50,
        )
        relevant = [item for item in transactions if item.amount.currency == currency]

        spent = sum_money(
            [item.amount for item in relevant if item.direction is Direction.DEBIT], currency
        )
        received = sum_money(
            [item.amount for item in relevant if item.direction is Direction.CREDIT], currency
        )

        per_category: dict[str, list[Money]] = {}
        for item in relevant:
            if item.direction is Direction.DEBIT:
                per_category.setdefault(item.category_id, []).append(item.amount)

        by_category = tuple(
            sorted(
                (
                    CategorySpending(
                        category_id=category,
                        total=sum_money(amounts, currency),
                        transaction_count=len(amounts),
                    )
                    for category, amounts in per_category.items()
                ),
                key=lambda entry: entry.total.minor_units,
                reverse=True,
            )
        )

        return SpendingSummary(
            currency=currency,
            period_start=since,
            period_end=until,
            total_spent=spent,
            total_received=received,
            transaction_count=len(relevant),
            by_category=by_category,
        )
