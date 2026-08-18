"""Vector index boundary.

The interface is deliberately narrow so the storage decision stays reversible:
MongoDB Atlas Vector Search is the intended production implementation, while
:class:`InMemoryVectorIndex` (brute-force cosine) backs tests and local
development.

The reference project loaded every vector into a Python list and scanned it on
each query. That is fine for a few hundred chunks and wrong for a growing
corpus, so ``search`` is defined as an index operation rather than a helper
over an in-process list.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from libra.ai.knowledge.indexing import IndexedChunkRef
from libra.ai.knowledge.models import (
    EmbeddedChunk,
    RetrievalFilters,
    RetrievalHit,
    RetrievalProfile,
)
from libra.ai.knowledge.retrieval import rank


class VectorIndex(ABC):
    @abstractmethod
    async def upsert(self, chunks: Sequence[EmbeddedChunk]) -> int: ...

    @abstractmethod
    async def delete(self, embedding_key: str, chunk_ids: Sequence[str]) -> int: ...

    @abstractmethod
    async def list_indexed(self, embedding_key: str) -> Sequence[IndexedChunkRef]: ...

    @abstractmethod
    async def search(
        self,
        *,
        query_vector: Sequence[float],
        embedding_key: str,
        filters: RetrievalFilters,
        profile: RetrievalProfile,
    ) -> Sequence[RetrievalHit]: ...


class InMemoryVectorIndex(VectorIndex):
    """Brute-force index for tests and local development."""

    def __init__(self) -> None:
        self._chunks: dict[tuple[str, str], EmbeddedChunk] = {}

    async def upsert(self, chunks: Sequence[EmbeddedChunk]) -> int:
        for chunk in chunks:
            self._chunks[(chunk.embedding_key, chunk.chunk.chunk_id)] = chunk
        return len(chunks)

    async def delete(self, embedding_key: str, chunk_ids: Sequence[str]) -> int:
        removed = 0
        for chunk_id in chunk_ids:
            if self._chunks.pop((embedding_key, chunk_id), None) is not None:
                removed += 1
        return removed

    async def list_indexed(self, embedding_key: str) -> Sequence[IndexedChunkRef]:
        return tuple(
            IndexedChunkRef(chunk_id=chunk.chunk.chunk_id, document_id=chunk.chunk.document_id)
            for (key, _), chunk in self._chunks.items()
            if key == embedding_key
        )

    async def search(
        self,
        *,
        query_vector: Sequence[float],
        embedding_key: str,
        filters: RetrievalFilters,
        profile: RetrievalProfile,
    ) -> Sequence[RetrievalHit]:
        return rank(
            query_vector=query_vector,
            chunks=tuple(self._chunks.values()),
            embedding_key=embedding_key,
            filters=filters,
            profile=profile,
        )
