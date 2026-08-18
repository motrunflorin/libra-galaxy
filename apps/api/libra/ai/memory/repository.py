"""User memory persistence contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from libra.ai.memory.models import MemoryKind, UserMemory


class UserMemoryRepository(ABC):
    @abstractmethod
    async def list_for_user(
        self, user_id: str, *, kinds: Sequence[MemoryKind] | None = None, limit: int = 20
    ) -> Sequence[UserMemory]: ...

    @abstractmethod
    async def upsert(self, memory: UserMemory) -> UserMemory: ...

    @abstractmethod
    async def delete(self, user_id: str, memory_id: str) -> None: ...


class InMemoryUserMemoryRepository(UserMemoryRepository):
    def __init__(self) -> None:
        self._items: dict[str, UserMemory] = {}

    async def list_for_user(
        self, user_id: str, *, kinds: Sequence[MemoryKind] | None = None, limit: int = 20
    ) -> Sequence[UserMemory]:
        selected = [
            memory
            for memory in self._items.values()
            if memory.user_id == user_id and (kinds is None or memory.kind in kinds)
        ]
        return selected[:limit]

    async def upsert(self, memory: UserMemory) -> UserMemory:
        self._items[memory.memory_id] = memory
        return memory

    async def delete(self, user_id: str, memory_id: str) -> None:
        existing = self._items.get(memory_id)
        if existing is not None and existing.user_id == user_id:
            del self._items[memory_id]
