"""RAG pipeline: chunking strategies, incremental indexing, filtered retrieval."""

from __future__ import annotations

from libra.ai.knowledge.chunking import (
    ChunkingPolicy,
    FixedWindowChunker,
    SectionAwareChunker,
    chunk_id_for,
)
from libra.ai.knowledge.indexing import IndexedChunkRef, plan_reindex
from libra.ai.knowledge.models import (
    Audience,
    Chunk,
    DocumentType,
    EmbeddedChunk,
    KnowledgeDocument,
    RetrievalFilters,
    RetrievalProfile,
)
from libra.ai.knowledge.retrieval import rank
from libra.ai.knowledge.service import cache_key_for
from libra.ai.knowledge.vector_index import InMemoryVectorIndex
from tests.conftest import ALICE, BOB, run


def _document(
    content: str,
    *,
    document_id: str = "doc",
    document_type: DocumentType = DocumentType.POLICY,
    language: str = "en",
    owner: str | None = None,
) -> KnowledgeDocument:
    return KnowledgeDocument(
        document_id=document_id,
        title="Title",
        document_type=document_type,
        language=language,
        content=content,
        owner_user_id=owner,
    )


# -- chunking ------------------------------------------------------------


def test_section_aware_chunker_keeps_headings_as_citable_sections() -> None:
    document = _document("# Fees\nCard fees are listed here.\n\n# Limits\nDaily limits apply.")
    chunks = SectionAwareChunker(size_tokens=200, overlap_tokens=20).split(document)

    assert [chunk.section for chunk in chunks] == ["Fees", "Limits"]
    assert all(chunk.document_id == "doc" for chunk in chunks)


def test_fixed_window_chunker_overlaps_windows() -> None:
    words = " ".join(f"w{index}" for index in range(400))
    chunks = FixedWindowChunker(size_tokens=40, overlap_tokens=20).split(_document(words))

    assert len(chunks) > 1
    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert set(first_words) & set(second_words)


def test_policy_selects_a_strategy_per_document_type() -> None:
    policy = ChunkingPolicy()
    assert policy.chunker_for(DocumentType.POLICY).name == "section_aware"
    assert policy.chunker_for(DocumentType.ACCOUNT_STATEMENT).name == "fixed_window"


def test_chunk_metadata_survives_chunking() -> None:
    document = _document("# Section\nBody text here.", language="ro", owner=ALICE)
    chunk = ChunkingPolicy().split(document)[0]

    assert chunk.language == "ro"
    assert chunk.owner_user_id == ALICE
    assert chunk.audience is Audience.CUSTOMER


def test_chunk_ids_are_content_addressed() -> None:
    assert chunk_id_for("doc", 0, "same") == chunk_id_for("doc", 0, "same")
    assert chunk_id_for("doc", 0, "same") != chunk_id_for("doc", 0, "different")


# -- incremental indexing ------------------------------------------------


def _chunks(document: KnowledgeDocument) -> list[Chunk]:
    return list(ChunkingPolicy().split(document))


def test_unchanged_documents_reuse_every_embedding() -> None:
    desired = _chunks(_document("# A\nAlpha content.\n\n# B\nBeta content."))
    indexed = [IndexedChunkRef(chunk.chunk_id, chunk.document_id) for chunk in desired]

    plan = plan_reindex(embedding_key="key", desired_chunks=desired, indexed=indexed)

    assert plan.is_noop is True
    assert len(plan.to_reuse) == len(desired)


def test_edited_section_only_re_embeds_what_changed() -> None:
    original = _chunks(_document("# A\nAlpha content.\n\n# B\nBeta content."))
    indexed = [IndexedChunkRef(chunk.chunk_id, chunk.document_id) for chunk in original]
    edited = _chunks(_document("# A\nAlpha content.\n\n# B\nBeta content changed."))

    plan = plan_reindex(embedding_key="key", desired_chunks=edited, indexed=indexed)

    assert len(plan.to_embed) == 1
    assert len(plan.to_reuse) == 1
    assert len(plan.to_delete) == 1


def test_removed_document_leaves_no_stale_chunks() -> None:
    indexed = [IndexedChunkRef("stale-1", "gone"), IndexedChunkRef("stale-2", "gone")]
    plan = plan_reindex(embedding_key="key", desired_chunks=[], indexed=indexed)

    assert plan.to_delete == ("stale-1", "stale-2")
    assert plan.to_embed == ()


def test_plans_are_computed_per_embedding_space() -> None:
    desired = _chunks(_document("# A\nAlpha."))
    index = InMemoryVectorIndex()
    run(
        index.upsert(
            [
                EmbeddedChunk(chunk=chunk, vector=(1.0, 0.0), embedding_key="model-a")
                for chunk in desired
            ]
        )
    )

    # Switching the embedding deployment must rebuild, not mix vector spaces.
    plan = plan_reindex(
        embedding_key="model-b",
        desired_chunks=desired,
        indexed=run(index.list_indexed("model-b")),
    )
    assert len(plan.to_embed) == len(desired)


def test_query_cache_key_never_contains_the_raw_query() -> None:
    key = cache_key_for("model-a", "how much did I spend at the pharmacy")
    assert "pharmacy" not in key
    assert key.startswith("model-a:")


# -- retrieval -----------------------------------------------------------


def _embedded(
    text: str,
    vector: tuple[float, ...],
    *,
    language: str = "en",
    document_type: DocumentType = DocumentType.FAQ,
    owner: str | None = None,
    audience: Audience = Audience.CUSTOMER,
    embedding_key: str = "key",
) -> EmbeddedChunk:
    chunk = Chunk(
        chunk_id=chunk_id_for("doc", 0, text),
        document_id="doc",
        position=0,
        text=text,
        language=language,
        document_type=document_type,
        audience=audience,
        owner_user_id=owner,
    )
    return EmbeddedChunk(chunk=chunk, vector=vector, embedding_key=embedding_key)


def test_min_score_and_top_k_come_from_the_profile() -> None:
    chunks = [
        _embedded("close", (1.0, 0.0)),
        _embedded("mid", (0.7, 0.7)),
        _embedded("far", (0.0, 1.0)),
    ]
    hits = rank(
        query_vector=(1.0, 0.0),
        chunks=chunks,
        embedding_key="key",
        filters=RetrievalFilters(),
        profile=RetrievalProfile(name="test", top_k=2, min_score=0.5),
    )

    assert [hit.chunk.text for hit in hits] == ["close", "mid"]


def test_language_filter_applies_before_similarity() -> None:
    chunks = [_embedded("english", (1.0, 0.0)), _embedded("romanian", (1.0, 0.0), language="ro")]
    hits = rank(
        query_vector=(1.0, 0.0),
        chunks=chunks,
        embedding_key="key",
        filters=RetrievalFilters(languages=("ro",)),
        profile=RetrievalProfile(name="test"),
    )

    assert [hit.chunk.text for hit in hits] == ["romanian"]


def test_user_documents_are_isolated_by_owner() -> None:
    chunks = [
        _embedded("alice statement", (1.0, 0.0), owner=ALICE),
        _embedded("bob statement", (1.0, 0.0), owner=BOB),
        _embedded("shared faq", (1.0, 0.0)),
    ]
    hits = rank(
        query_vector=(1.0, 0.0),
        chunks=chunks,
        embedding_key="key",
        filters=RetrievalFilters(owner_user_id=ALICE),
        profile=RetrievalProfile(name="test"),
    )
    texts = {hit.chunk.text for hit in hits}

    assert texts == {"alice statement", "shared faq"}


def test_staff_only_content_is_not_returned_to_customers() -> None:
    chunks = [_embedded("internal procedure", (1.0, 0.0), audience=Audience.STAFF)]
    hits = rank(
        query_vector=(1.0, 0.0),
        chunks=chunks,
        embedding_key="key",
        filters=RetrievalFilters(audience=Audience.CUSTOMER),
        profile=RetrievalProfile(name="test"),
    )

    assert hits == []


def test_vectors_from_another_embedding_space_are_never_compared() -> None:
    chunks = [_embedded("other model", (1.0, 0.0), embedding_key="other")]
    hits = rank(
        query_vector=(1.0, 0.0),
        chunks=chunks,
        embedding_key="key",
        filters=RetrievalFilters(),
        profile=RetrievalProfile(name="test"),
    )

    assert hits == []


def test_hits_carry_a_citation() -> None:
    hits = rank(
        query_vector=(1.0, 0.0),
        chunks=[_embedded("cite me", (1.0, 0.0))],
        embedding_key="key",
        filters=RetrievalFilters(),
        profile=RetrievalProfile(name="test"),
    )

    assert hits[0].citation.startswith("doc@v")
