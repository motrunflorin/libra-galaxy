"""Chunking strategies.

The reference project applied one word-window to every document. Banking
content is not uniform — a policy has sections, a statement has rows, an FAQ
has question/answer pairs — so chunking is a strategy chosen per document
type, with size and overlap kept configurable.

Chunk metadata (document, position, language, section, audience, owner) is
preserved through the pipeline, because retrieval filters and citations depend
on it.
"""

from __future__ import annotations

import hashlib
import re
from typing import Protocol, Sequence

from libra.ai.knowledge.models import Chunk, DocumentType, KnowledgeDocument
from libra.core.errors import ValidationError

#: Rough tokens-per-character ratio used to size windows without a tokenizer.
#: Deliberately approximate: exact token budgets are enforced downstream by
#: the context builder, which counts real tokens.
_CHARS_PER_TOKEN = 4

_SECTION_PATTERN = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)


def chunk_id_for(document_id: str, position: int, text: str) -> str:
    """Content-addressed chunk id.

    Because the id derives from the text, an unchanged chunk keeps its id
    across re-indexing runs and its embedding can be reused (see
    :mod:`libra.ai.knowledge.indexing`).
    """
    payload = f"{document_id}\0{position}\0{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class Chunker(Protocol):
    name: str

    def split(self, document: KnowledgeDocument) -> Sequence[Chunk]: ...


class FixedWindowChunker:
    """Overlapping windows over words. The general-purpose default."""

    name = "fixed_window"

    def __init__(self, size_tokens: int = 320, overlap_tokens: int = 60) -> None:
        if size_tokens <= 0:
            raise ValidationError("Chunk size must be positive.")
        if not 0 <= overlap_tokens < size_tokens:
            raise ValidationError("Chunk overlap must be smaller than the chunk size.")
        self._size_words = max(1, size_tokens * _CHARS_PER_TOKEN // 5)
        self._overlap_words = max(0, overlap_tokens * _CHARS_PER_TOKEN // 5)

    def split(self, document: KnowledgeDocument) -> Sequence[Chunk]:
        words = document.content.split()
        if not words:
            return ()

        step = self._size_words - self._overlap_words
        chunks: list[Chunk] = []
        position = 0

        for start in range(0, len(words), step):
            window = words[start : start + self._size_words]
            if not window:
                break
            text = " ".join(window)
            chunks.append(_build_chunk(document, position, text))
            position += 1
            if start + self._size_words >= len(words):
                break

        return tuple(chunks)


class SectionAwareChunker:
    """Splits on Markdown headings, then windows any oversized section.

    Used for policies and procedures, where a section boundary is a meaning
    boundary and citing the section is what makes an answer verifiable.
    """

    name = "section_aware"

    def __init__(self, size_tokens: int = 320, overlap_tokens: int = 60) -> None:
        self._window = FixedWindowChunker(size_tokens, overlap_tokens)
        self._max_chars = size_tokens * _CHARS_PER_TOKEN

    def split(self, document: KnowledgeDocument) -> Sequence[Chunk]:
        sections = _split_sections(document.content)
        if not sections:
            return self._window.split(document)

        chunks: list[Chunk] = []
        position = 0

        for heading, body in sections:
            text = body.strip()
            if not text:
                continue
            if len(text) <= self._max_chars:
                chunks.append(_build_chunk(document, position, text, section=heading))
                position += 1
                continue

            sub_document = KnowledgeDocument(
                document_id=document.document_id,
                title=document.title,
                document_type=document.document_type,
                language=document.language,
                content=text,
                version=document.version,
                audience=document.audience,
                owner_user_id=document.owner_user_id,
            )
            for sub_chunk in self._window.split(sub_document):
                chunks.append(
                    _build_chunk(document, position, sub_chunk.text, section=heading)
                )
                position += 1

        return tuple(chunks)


#: Which strategy handles which document type. Extending this map is how a
#: statement-specific or semantic chunker is introduced later.
DEFAULT_STRATEGIES: dict[DocumentType, str] = {
    DocumentType.POLICY: SectionAwareChunker.name,
    DocumentType.PROCEDURE: SectionAwareChunker.name,
    DocumentType.PRODUCT: SectionAwareChunker.name,
    DocumentType.FAQ: SectionAwareChunker.name,
    DocumentType.FINANCIAL_EDUCATION: FixedWindowChunker.name,
    DocumentType.USER_DOCUMENT: FixedWindowChunker.name,
    DocumentType.ACCOUNT_STATEMENT: FixedWindowChunker.name,
}


class ChunkingPolicy:
    """Selects a chunker per document type."""

    def __init__(
        self,
        *,
        size_tokens: int = 320,
        overlap_tokens: int = 60,
        strategies: dict[DocumentType, str] | None = None,
    ) -> None:
        self._chunkers: dict[str, Chunker] = {
            FixedWindowChunker.name: FixedWindowChunker(size_tokens, overlap_tokens),
            SectionAwareChunker.name: SectionAwareChunker(size_tokens, overlap_tokens),
        }
        self._strategies = {**DEFAULT_STRATEGIES, **(strategies or {})}

    def chunker_for(self, document_type: DocumentType) -> Chunker:
        name = self._strategies.get(document_type, FixedWindowChunker.name)
        return self._chunkers[name]

    def split(self, document: KnowledgeDocument) -> Sequence[Chunk]:
        return self.chunker_for(document.document_type).split(document)


def _split_sections(content: str) -> list[tuple[str, str]]:
    matches = list(_SECTION_PATTERN.finditer(content))
    if not matches:
        return []

    sections: list[tuple[str, str]] = []
    preamble = content[: matches[0].start()].strip()
    if preamble:
        sections.append(("", preamble))

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        sections.append((match.group(2).strip(), content[match.end() : end]))

    return sections


def _build_chunk(
    document: KnowledgeDocument, position: int, text: str, *, section: str = ""
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id_for(document.document_id, position, text),
        document_id=document.document_id,
        position=position,
        text=text,
        language=document.language,
        document_type=document.document_type,
        audience=document.audience,
        section=section,
        owner_user_id=document.owner_user_id,
        metadata={"title": document.title, "version": document.version},
    )
