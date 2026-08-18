"""In-process user repository for local development and tests."""

from __future__ import annotations

from libra.domains.identity.models import User
from libra.domains.identity.repository import UserRepository


class InMemoryUserRepository(UserRepository):
    def __init__(self, users: list[User] | None = None) -> None:
        self._users: dict[str, User] = {user.user_id: user for user in users or []}

    async def get(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()
        for user in self._users.values():
            if user.email.lower() == normalized:
                return user
        return None

    async def upsert(self, user: User) -> User:
        self._users[user.user_id] = user
        return user
