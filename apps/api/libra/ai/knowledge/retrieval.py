"""Retrieval: filter first, then rank.

Metadata filters (language, document type, audience, document owner) are
applied *before* similarity so an isolation rule can never be outranked by a
high cosine score. Thresholds and ``top_k`` come from a named
:class:`RetrievalProfile` rather than one global constant.

Reranking is a deliberate seam: :func:`rank` returns scored hits, and a
reranker can be inserted between filtering and context injection without
changing callers.
"""

from __future__ import annotations

import math
from typing import Sequence

from libra.ai.knowledge.models import (
    EmbeddedChunk,
    RetrievalFilters,
    RetrievalHit,
    RetrievalProfile,
)


def cosine_similarity(first: Sequence[float], second: Sequence[float]) -> float:
    if not first or not second or len(first) != len(second):
        return 0.0
    dot = sum(a * b for a, b in zip(first, second))
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    if first_norm == 0.0 or second_norm == 0.0:
        return 0.0
    return dot / (first_norm * second_norm)


def matches(chunk: EmbeddedChunk, filters: RetrievalFilters, embedding_key: str) -> bool:
    """Decide whether a stored chunk is admissible for this query."""
    if chunk.embedding_key != embedding_key:
        # Never compare vectors produced by different models or versions.
        return False

    metadata = chunk.chunk

    if filters.languages and metadata.language not in filters.languages:
        return False

    if filters.document_types and metadata.document_type not in filters.document_types:
        return False

    if metadata.audience is not filters.audience:
        return False

    # User-owned documents are visible only to their owner; shared knowledge
    # (owner_user_id is None) is visible to everyone the audience allows.
    if metadata.owner_user_id is not None and metadata.owner_user_id != filters.owner_user_id:
        return False

    for key, expected in filters.metadata_equals.items():
        if metadata.metadata.get(key) != expected:
            return False

    return True


def rank(
    *,
    query_vector: Sequence[float],
    chunks: Sequence[EmbeddedChunk],
    embedding_key: str,
    filters: RetrievalFilters,
    profile: RetrievalProfile,
) -> list[RetrievalHit]:
    """Return the admissible chunks above the profile threshold, best first."""
    hits: list[RetrievalHit] = []

    for chunk in chunks:
        if not matches(chunk, filters, embedding_key):
            continue
        score = cosine_similarity(query_vector, chunk.vector)
        if score < profile.min_score:
            continue
        hits.append(
            RetrievalHit(
                chunk=chunk.chunk, score=score, document_version=chunk.document_version
            )
        )

    hits.sort(key=lambda hit: hit.score, reverse=True)
    return _cap_chars(hits[: profile.top_k], profile.max_chars)


def _cap_chars(hits: Sequence[RetrievalHit], max_chars: int) -> list[RetrievalHit]:
    """Drop trailing hits once the character budget is exhausted."""
    kept: list[RetrievalHit] = []
    used = 0
    for hit in hits:
        size = len(hit.chunk.text)
        if used + size > max_chars:
            break
        kept.append(hit)
        used += size
    return kept
