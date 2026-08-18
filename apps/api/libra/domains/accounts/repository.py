"""Account persistence contract.

Every read is scoped by ``user_id``: user isolation is enforced in the query,
not only by a check after loading.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from libra.domains.accounts.models import Account, Subaccount


class AccountRepository(ABC):
    @abstractmethod
    async def list_for_user(self, user_id: str) -> Sequence[Account]: ...

    @abstractmethod
    async def get_for_user(self, user_id: str, account_id: str) -> Account | None: ...

    @abstractmethod
    async def list_subaccounts(self, user_id: str, account_id: str) -> Sequence[Subaccount]: ...
