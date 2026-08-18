"""Identity application service."""

from __future__ import annotations

from libra.core.errors import ResourceNotFoundError
from libra.core.security.authorization import require_ownership
from libra.core.security.principal import Principal
from libra.domains.identity.models import User
from libra.domains.identity.repository import UserRepository


class IdentityService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def get_user(self, principal: Principal, user_id: str) -> User:
        """Read a user profile. Customers may only read their own."""
        require_ownership(principal, user_id)
        user = await self._users.get(user_id)
        if user is None:
            raise ResourceNotFoundError()
        return user

    async def resolve_for_authentication(self, user_id: str) -> User | None:
        """Used by the authentication layer before a principal exists.

        Deliberately not exposed through any router.
        """
        return await self._users.get(user_id)
