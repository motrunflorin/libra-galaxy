"""MongoDB client boundary.

The driver is imported lazily so that unit tests, the in-memory backend and
CLI commands never require a running MongoDB. Nothing outside this module and
``*_repository.py`` implementations may import ``motor``/``pymongo`` — the rule
is enforced by ``tests/test_architecture_boundaries.py``.
"""

from __future__ import annotations

from typing import Any

from libra.core.config import MongoSettings
from libra.core.errors import PersistenceError
from libra.core.persistence.indexes import INDEX_SPECS


class MongoDatabaseProvider:
    """Owns the single Motor client for the process."""

    def __init__(self, settings: MongoSettings) -> None:
        self._settings = settings
        self._client: Any | None = None

    def database(self) -> Any:
        if self._client is None:
            try:
                from motor.motor_asyncio import AsyncIOMotorClient
            except ImportError as error:  # pragma: no cover - depends on install
                raise PersistenceError(
                    "The MongoDB driver is not installed but the mongo backend is selected."
                ) from error
            self._client = AsyncIOMotorClient(self._settings.uri, tz_aware=True)
        return self._client[self._settings.database]

    async def ping(self) -> bool:
        try:
            await self.database().command("ping")
            return True
        except Exception:
            return False

    async def ensure_indexes(self) -> int:
        """Apply every declared index. Safe to run repeatedly."""
        database = self.database()
        for spec in INDEX_SPECS:
            options: dict[str, Any] = {"name": spec.name, "unique": spec.unique}
            if spec.expire_after_seconds is not None:
                options["expireAfterSeconds"] = spec.expire_after_seconds
            if spec.partial_filter:
                options["partialFilterExpression"] = spec.partial_filter
            await database[spec.collection].create_index(list(spec.keys), **options)
        return len(INDEX_SPECS)

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
