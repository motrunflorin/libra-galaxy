"""Incremental re-indexing.

Adapted from the reference project's content-hash approach, with the
embedding space made explicit: a plan is always computed *for one
``embedding_key``* (provider:deployment:version). Changing the embedding
deployment therefore produces a full rebuild for the new key instead of
silently mixing incompatible vectors — the failure mode the reference
implementation had when it swapped provider mid-run.

``plan_reindex`` is a pure function, so re-indexing behaviour is unit-testable
without a database or an embedding provider.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Sequence

from libra.ai.knowledge.models import Chunk


def content_checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class IndexedChunkRef:
    """What the store already holds for one embedding key."""

    chunk_id: str
    document_id: str


@dataclass(frozen=True)
class ReindexPlan:
    """The work required to bring one embedding space up to date."""

    embedding_key: str
    #: Chunks that need embedding because they are new or changed.
    to_embed: tuple[Chunk, ...]
    #: Chunk ids that are still valid and keep their existing vectors.
    to_reuse: tuple[str, ...]
    #: Chunk ids to delete: their document changed or was removed.
    to_delete: tuple[str, ...]

    @property
    def is_noop(self) -> bool:
        return not self.to_embed and not self.to_delete

    def report(self) -> dict[str, int | str]:
        return {
            "embedding_key": self.embedding_key,
            "embed": len(self.to_embed),
            "reuse": len(self.to_reuse),
            "delete": len(self.to_delete),
        }


def plan_reindex(
    *,
    embedding_key: str,
    desired_chunks: Sequence[Chunk],
    indexed: Iterable[IndexedChunkRef],
) -> ReindexPlan:
    """Compare desired chunks against what is indexed for this embedding key.

    Because chunk ids are content-addressed, an unchanged chunk appears in
    both sets and is reused; an edited paragraph produces a new id (embed) and
    leaves its old id behind (delete).
    """
    desired_by_id = {chunk.chunk_id: chunk for chunk in desired_chunks}
    indexed_ids = {ref.chunk_id for ref in indexed}

    to_embed = tuple(
        chunk for chunk_id, chunk in desired_by_id.items() if chunk_id not in indexed_ids
    )
    to_reuse = tuple(sorted(chunk_id for chunk_id in desired_by_id if chunk_id in indexed_ids))
    to_delete = tuple(sorted(indexed_ids - set(desired_by_id)))

    return ReindexPlan(
        embedding_key=embedding_key,
        to_embed=to_embed,
        to_reuse=to_reuse,
        to_delete=to_delete,
    )


def batched(items: Sequence[Chunk], size: int) -> list[Sequence[Chunk]]:
    """Split embedding work into provider-sized batches."""
    if size <= 0:
        raise ValueError("Batch size must be positive.")
    return [items[start : start + size] for start in range(0, len(items), size)]
