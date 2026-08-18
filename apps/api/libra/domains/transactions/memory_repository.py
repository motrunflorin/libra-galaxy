"""In-process transaction repository for local development and tests."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from libra.domains.transactions.models import Transaction
from libra.domains.transactions.repository import TransactionRepository


class InMemoryTransactionRepository(TransactionRepository):
    def __init__(self, transactions: Sequence[Transaction] = ()) -> None:
        self._transactions = list(transactions)

    def _match(
        self,
        user_id: str,
        account_id: str | None,
        since: datetime | None,
        until: datetime | None,
    ) -> list[Transaction]:
        return [
            transaction
            for transaction in self._transactions
            if transaction.user_id == user_id
            and (account_id is None or transaction.account_id == account_id)
            and (since is None or transaction.booked_at >= since)
            and (until is None or transaction.booked_at < until)
        ]

    async def list_for_user(
        self,
        user_id: str,
        *,
        account_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Transaction]:
        matched = self._match(user_id, account_id, since, until)
        matched.sort(key=lambda item: item.booked_at, reverse=True)
        return matched[offset : offset + limit]

    async def count_for_user(
        self,
        user_id: str,
        *,
        account_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> int:
        return len(self._match(user_id, account_id, since, until))
