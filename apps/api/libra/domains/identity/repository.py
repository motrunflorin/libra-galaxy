"""Identity persistence contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from libra.domains.identity.models import User


class UserRepository(ABC):
    @abstractmethod
    async def get(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def upsert(self, user: User) -> User: ...
