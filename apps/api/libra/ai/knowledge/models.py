"""Knowledge and retrieval models.

Metadata is preserved from ingestion through to the cited answer: a retrieved
chunk always knows its document, version, language and section, so an answer
can be attributed and a stale document can be invalidated precisely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DocumentType(str, Enum):
    POLICY = "policy"
    PROCEDURE = "procedure"
    PRODUCT = "product"
    FAQ = "faq"
    FINANCIAL_EDUCATION = "financial_education"
    #: A document uploaded by a user; always user-scoped at retrieval time.
    USER_DOCUMENT = "user_document"
    ACCOUNT_STATEMENT = "account_statement"


class Audience(str, Enum):
    """Who may retrieve a document. Enforced as a retrieval filter."""

    CUSTOMER = "customer"
    STAFF = "staff"


@dataclass(frozen=True)
class KnowledgeDocument:
    document_id: str
    title: str
    document_type: DocumentType
    language: str
    content: str
    version: str = "1"
    audience: Audience = Audience.CUSTOMER
    source: str = ""
    #: Content hash: the basis for incremental re-indexing.
    checksum: str = ""
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    #: Present only for user documents; enforces per-user retrieval isolation.
    owner_user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    """A chunk before embedding."""

    chunk_id: str
    document_id: str
    position: int
    text: str
    language: str
    document_type: DocumentType
    audience: Audience = Audience.CUSTOMER
    section: str = ""
    owner_user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EmbeddedChunk:
    """A chunk with its vector and the identity of the vector space.

    ``embedding_key`` (provider:deployment:version) is stored with every
    vector so vectors from different models are never compared.
    """

    chunk: Chunk
    vector: tuple[float, ...]
    embedding_key: str
    document_version: str = "1"
    indexed_at: datetime | None = None


@dataclass(frozen=True)
class RetrievalFilters:
    """Filters applied *before* similarity, not after.

    ``owner_user_id`` is the isolation boundary for user documents: shared
    knowledge has no owner, a user document is only visible to its owner.
    """

    languages: tuple[str, ...] = ()
    document_types: tuple[DocumentType, ...] = ()
    audience: Audience = Audience.CUSTOMER
    owner_user_id: str | None = None
    metadata_equals: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalProfile:
    """Per-corpus retrieval tuning.

    One global threshold is not appropriate for every corpus, so profiles are
    named and configurable, and evaluation can tune them independently.
    """

    name: str
    top_k: int = 5
    min_score: float = 0.30
    max_chars: int = 7_000


@dataclass(frozen=True)
class RetrievalHit:
    chunk: Chunk
    score: float
    document_version: str = "1"

    @property
    def citation(self) -> str:
        section = f"#{self.chunk.section}" if self.chunk.section else ""
        return f"{self.chunk.document_id}{section}@v{self.document_version}"
