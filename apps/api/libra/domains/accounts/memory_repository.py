"""In-process account repository for local development and tests."""

from __future__ import annotations

from typing import Sequence

from libra.domains.accounts.models import Account, Subaccount
from libra.domains.accounts.repository import AccountRepository


class InMemoryAccountRepository(AccountRepository):
    def __init__(
        self,
        accounts: Sequence[Account] = (),
        subaccounts: Sequence[Subaccount] = (),
    ) -> None:
        self._accounts = list(accounts)
        self._subaccounts = list(subaccounts)

    async def list_for_user(self, user_id: str) -> Sequence[Account]:
        return [account for account in self._accounts if account.user_id == user_id]

    async def get_for_user(self, user_id: str, account_id: str) -> Account | None:
        for account in self._accounts:
            if account.account_id == account_id and account.user_id == user_id:
                return account
        return None

    async def list_subaccounts(self, user_id: str, account_id: str) -> Sequence[Subaccount]:
        return [
            item
            for item in self._subaccounts
            if item.user_id == user_id and item.account_id == account_id
        ]
