"""Account application service — the authoritative source for balances."""

from __future__ import annotations

from typing import Sequence

from libra.core.errors import ResourceNotFoundError
from libra.core.money import Money, sum_money
from libra.core.security.authorization import require_permission
from libra.core.security.principal import Permission, Principal
from libra.domains.accounts.models import Account, Subaccount
from libra.domains.accounts.repository import AccountRepository


class AccountService:
    """Reads are permission-checked and user-scoped, without exception.

    Both the HTTP routers and the AI tool layer call this service; there is no
    second implementation and no path that skips these checks.
    """

    def __init__(self, accounts: AccountRepository) -> None:
        self._accounts = accounts

    async def list_accounts(self, principal: Principal) -> Sequence[Account]:
        require_permission(principal, Permission.ACCOUNTS_READ)
        return await self._accounts.list_for_user(principal.user_id)

    async def get_account(self, principal: Principal, account_id: str) -> Account:
        require_permission(principal, Permission.ACCOUNTS_READ)
        account = await self._accounts.get_for_user(principal.user_id, account_id)
        if account is None:
            # Not-found rather than forbidden: another user's identifier must
            # not be distinguishable from a non-existent one.
            raise ResourceNotFoundError()
        return account

    async def list_subaccounts(self, principal: Principal, account_id: str) -> Sequence[Subaccount]:
        await self.get_account(principal, account_id)
        return await self._accounts.list_subaccounts(principal.user_id, account_id)

    async def total_balance(self, principal: Principal, currency: str) -> Money:
        """Deterministic sum across the user's accounts in one currency."""
        accounts = await self.list_accounts(principal)
        return sum_money(
            [account.balance for account in accounts if account.currency == currency],
            currency,
        )
