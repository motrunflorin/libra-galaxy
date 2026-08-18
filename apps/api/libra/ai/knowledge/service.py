"""Knowledge service: indexing and retrieval wiring.

Holds the pipeline together — catalogue -> chunking -> embedding -> index, and
query -> embedding (cached) -> filtered retrieval — while keeping every stage
independently testable.

The embedding cache is keyed by ``embedding_key`` plus a content hash, so a
deployment or version change never reuses an incompatible vector. Cached query
vectors are stored under a hash of the query text: the plaintext of a user's
question is never persisted in the cache.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Protocol, Sequence

from libra.ai.knowledge.chunking import ChunkingPolicy
from libra.ai.knowledge.indexing import ReindexPlan, batched, plan_reindex
from libra.ai.knowledge.models import (
    EmbeddedChunk,
    KnowledgeDocument,
    RetrievalFilters,
    RetrievalHit,
    RetrievalProfile,
)
from libra.ai.knowledge.vector_index import VectorIndex
from libra.ai.providers.base import EmbeddingProvider
from libra.core.errors import RetrievalError
from libra.core.logging import log_event

LOGGER = logging.getLogger("libra.ai.knowledge")


class EmbeddingCache(Protocol):
    """Vector reuse across runs. Keys are hashes, never raw text."""

    async def get(self, cache_key: str) -> tuple[float, ...] | None: ...

    async def put(self, cache_key: str, vector: Sequence[float]) -> None: ...


class InMemoryEmbeddingCache:
    def __init__(self) -> None:
        self._items: dict[str, tuple[float, ...]] = {}

    async def get(self, cache_key: str) -> tuple[float, ...] | None:
        return self._items.get(cache_key)

    async def put(self, cache_key: str, vector: Sequence[float]) -> None:
        self._items[cache_key] = tuple(vector)


def cache_key_for(embedding_key: str, text: str) -> str:
    digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
    return f"{embedding_key}:{digest}"


class KnowledgeService:
    def __init__(
        self,
        *,
        embeddings: EmbeddingProvider,
        index: VectorIndex,
        chunking: ChunkingPolicy,
        cache: EmbeddingCache | None = None,
        batch_size: int = 16,
    ) -> None:
        self._embeddings = embeddings
        self._index = index
        self._chunking = chunking
        self._cache = cache or InMemoryEmbeddingCache()
        self._batch_size = max(1, batch_size)

    @property
    def embedding_key(self) -> str:
        return self._embeddings.embedding_key

    async def plan(self, documents: Sequence[KnowledgeDocument]) -> ReindexPlan:
        """Compute the work required without calling the embedding provider."""
        desired = [chunk for document in documents for chunk in self._chunking.split(document)]
        indexed = await self._index.list_indexed(self.embedding_key)
        return plan_reindex(
            embedding_key=self.embedding_key, desired_chunks=desired, indexed=indexed
        )

    async def reindex(self, documents: Sequence[KnowledgeDocument]) -> dict[str, int | str]:
        """Apply an incremental plan: embed new chunks, drop stale ones."""
        plan = await self.plan(documents)
        embedded_count = 0

        for batch in batched(plan.to_embed, self._batch_size):
            result = await self._embeddings.embed([chunk.text for chunk in batch])
            now = datetime.now(timezone.utc)
            await self._index.upsert(
                [
                    EmbeddedChunk(
                        chunk=chunk,
                        vector=vector,
                        embedding_key=result.embedding_key,
                        document_version=str(chunk.metadata.get("version", "1")),
                        indexed_at=now,
                    )
                    for chunk, vector in zip(batch, result.vectors)
                ]
            )
            embedded_count += len(batch)

        if plan.to_delete:
            await self._index.delete(plan.embedding_key, plan.to_delete)

        report = {**plan.report(), "embedded": embedded_count}
        log_event(LOGGER, "knowledge.reindexed", **report)
        return report

    async def search(
        self,
        query: str,
        *,
        filters: RetrievalFilters,
        profile: RetrievalProfile,
    ) -> Sequence[RetrievalHit]:
        clean = query.strip()
        if not clean:
            return ()

        key = cache_key_for(self.embedding_key, clean)
        vector = await self._cache.get(key)

        if vector is None:
            try:
                result = await self._embeddings.embed([clean])
            except Exception as error:  # noqa: BLE001 - normalized for the caller
                raise RetrievalError("The query could not be embedded.") from error
            vector = result.vectors[0]
            await self._cache.put(key, vector)

        return await self._index.search(
            query_vector=vector,
            embedding_key=self.embedding_key,
            filters=filters,
            profile=profile,
        )
