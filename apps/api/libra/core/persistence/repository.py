"""Repository contracts shared by every domain.

Application services depend on these abstractions; only implementations under
``*_repository.py`` know about MongoDB. This keeps a future move of the ledger
to a transactional store a repository-level change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    """One page of results plus the information needed to request the next."""

    items: Sequence[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total
