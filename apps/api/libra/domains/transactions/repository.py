"""Transaction persistence contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Sequence

from libra.domains.transactions.models import Transaction


class TransactionRepository(ABC):
    @abstractmethod
    async def list_for_user(
        self,
        user_id: str,
        *,
        account_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Transaction]: ...

    @abstractmethod
    async def count_for_user(
        self,
        user_id: str,
        *,
        account_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> int: ...
