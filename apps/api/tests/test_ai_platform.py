"""AI platform pieces that later phases wire in: providers, RAG service,
workflow state, cost tracking and user-scoped memory."""

from __future__ import annotations

import pytest

from libra.ai.knowledge.chunking import ChunkingPolicy
from libra.ai.knowledge.models import (
    Audience,
    DocumentType,
    KnowledgeDocument,
    RetrievalFilters,
    RetrievalProfile,
)
from libra.ai.knowledge.service import InMemoryEmbeddingCache, KnowledgeService
from libra.ai.knowledge.vector_index import InMemoryVectorIndex
from libra.ai.memory.models import MemoryKind, UserMemory
from libra.ai.memory.repository import InMemoryUserMemoryRepository
from libra.ai.orchestration.workflow import StepKind, StepStatus, WorkflowRun, WorkflowStep
from libra.ai.providers.base import ChatMessage, ChatRole, EmbeddingBatch, TokenUsage
from libra.ai.providers.foundry.chat import MicrosoftFoundryChatProvider
from libra.ai.providers.foundry.embeddings import MicrosoftFoundryEmbeddingProvider
from libra.ai.providers.tokens import TokenCounter, estimate_chat_cost, estimate_embedding_cost
from libra.core.config import load_settings
from libra.core.errors import AIProviderUnavailableError
from tests.conftest import ALICE, BOB, run


# -- providers -----------------------------------------------------------


def test_unconfigured_foundry_fails_cleanly_and_does_not_fall_back() -> None:
    """No provider fallback: unavailability is an error, not a silent switch."""
    settings = load_settings({})
    chat = MicrosoftFoundryChatProvider(settings.foundry)
    embeddings = MicrosoftFoundryEmbeddingProvider(settings.foundry)

    with pytest.raises(AIProviderUnavailableError):
        run(chat.complete([ChatMessage(ChatRole.USER, "hello")]))

    with pytest.raises(AIProviderUnavailableError):
        run(embeddings.embed(["hello"]))


def test_deployment_names_come_from_configuration() -> None:
    settings = load_settings(
        {
            "LIBRA_FOUNDRY_CHAT_DEPLOYMENT": "gpt-5-mini-eu",
            "LIBRA_FOUNDRY_EMBEDDING_DEPLOYMENT": "text-embedding-3-small-eu",
            "LIBRA_EMBEDDING_VERSION": "v2",
        }
    )
    assert MicrosoftFoundryChatProvider(settings.foundry).deployment == "gpt-5-mini-eu"

    embeddings = MicrosoftFoundryEmbeddingProvider(settings.foundry)
    # The embedding key pins provider, deployment and version together, so
    # vectors from an older configuration are never reused.
    assert embeddings.embedding_key == "microsoft_foundry:text-embedding-3-small-eu:v2"


# -- token counting and cost --------------------------------------------


def test_token_counting_works_without_the_optional_tokenizer() -> None:
    counter = TokenCounter()
    assert counter.count_text("") == 0
    assert counter.count_text("a reasonably long sentence about money") > 3
    assert counter.count_messages([ChatMessage(ChatRole.USER, "hi")]) > 0


def test_cost_is_estimated_from_configured_rates() -> None:
    settings = load_settings(
        {
            "LIBRA_AI_INPUT_PRICE_PER_MILLION": "1.0",
            "LIBRA_AI_CACHED_INPUT_PRICE_PER_MILLION": "0.1",
            "LIBRA_AI_OUTPUT_PRICE_PER_MILLION": "2.0",
        }
    ).ai

    usage = TokenUsage(input_tokens=1_000_000, cached_input_tokens=500_000, output_tokens=1_000_000)
    estimate = estimate_chat_cost(usage, settings)

    # 500k uncached @ $1 + 500k cached @ $0.1 + 1M output @ $2
    assert estimate.input_usd == pytest.approx(0.55)
    assert estimate.output_usd == pytest.approx(2.0)
    assert estimate.total_usd == pytest.approx(2.55)


def test_embedding_cost_has_no_output_component() -> None:
    settings = load_settings({"LIBRA_AI_EMBEDDING_PRICE_PER_MILLION": "0.02"}).ai
    estimate = estimate_embedding_cost(TokenUsage(input_tokens=1_000_000), settings)
    assert estimate.total_usd == pytest.approx(0.02)


# -- knowledge service ---------------------------------------------------


class _FakeEmbeddingProvider:
    """Deterministic stand-in: a vector derived from the text's own words.

    Lets the whole RAG pipeline be exercised without a provider or a network.
    """

    name = "fake"
    embedding_key = "fake:test:v1"

    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, texts):
        self.calls += 1
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append(
                (
                    float(lowered.count("subaccount") + lowered.count("subcont")),
                    float(lowered.count("allocation") + lowered.count("alocare")),
                    1.0,
                )
            )
        return EmbeddingBatch(
            vectors=tuple(vectors),
            provider="fake",
            deployment="test",
            embedding_version="v1",
            usage=TokenUsage(input_tokens=len(texts)),
        )


def _service(provider: _FakeEmbeddingProvider) -> KnowledgeService:
    return KnowledgeService(
        embeddings=provider,
        index=InMemoryVectorIndex(),
        chunking=ChunkingPolicy(size_tokens=200, overlap_tokens=20),
        cache=InMemoryEmbeddingCache(),
    )


def _corpus() -> list[KnowledgeDocument]:
    return [
        KnowledgeDocument(
            document_id="product_en",
            title="Product",
            document_type=DocumentType.FAQ,
            language="en",
            content="# Subaccounts\nA subaccount separates money by purpose.\n\n"
            "# Allocation rules\nAn allocation rule splits incoming money.",
        ),
        KnowledgeDocument(
            document_id="product_ro",
            title="Produs",
            document_type=DocumentType.FAQ,
            language="ro",
            content="# Subconturi\nUn subcont separa banii dupa scop.\n\n"
            "# Reguli de alocare\nO regula de alocare imparte banii primiti.",
        ),
    ]


def test_reindex_embeds_then_reuses() -> None:
    provider = _FakeEmbeddingProvider()
    service = _service(provider)
    corpus = _corpus()

    first = run(service.reindex(corpus))
    assert first["embed"] == 4
    assert first["embedded"] == 4
    assert first["delete"] == 0

    # A second run over unchanged documents must not call the provider again.
    calls_after_first = provider.calls
    second = run(service.reindex(corpus))
    assert second["embed"] == 0
    assert second["reuse"] == 4
    assert provider.calls == calls_after_first


def test_editing_one_section_re_embeds_only_that_section() -> None:
    provider = _FakeEmbeddingProvider()
    service = _service(provider)
    corpus = _corpus()
    run(service.reindex(corpus))

    edited = list(corpus)
    edited[0] = KnowledgeDocument(
        document_id="product_en",
        title="Product",
        document_type=DocumentType.FAQ,
        language="en",
        content="# Subaccounts\nA subaccount separates money by purpose.\n\n"
        "# Allocation rules\nAn allocation rule splits incoming money automatically.",
    )

    report = run(service.reindex(edited))
    assert report["embed"] == 1
    assert report["reuse"] == 3
    assert report["delete"] == 1


def test_search_respects_the_language_filter() -> None:
    service = _service(_FakeEmbeddingProvider())
    run(service.reindex(_corpus()))

    hits = run(
        service.search(
            "subcont",
            filters=RetrievalFilters(languages=("ro",), audience=Audience.CUSTOMER),
            profile=RetrievalProfile(name="product", top_k=3, min_score=0.1),
        )
    )

    assert hits
    assert all(hit.chunk.language == "ro" for hit in hits)


def test_query_embeddings_are_cached() -> None:
    provider = _FakeEmbeddingProvider()
    service = _service(provider)
    run(service.reindex(_corpus()))

    profile = RetrievalProfile(name="product", top_k=3, min_score=0.1)
    calls_before = provider.calls
    run(service.search("subaccount", filters=RetrievalFilters(), profile=profile))
    after_first_query = provider.calls
    run(service.search("subaccount", filters=RetrievalFilters(), profile=profile))

    assert after_first_query == calls_before + 1
    assert provider.calls == after_first_query  # served from cache


def test_empty_query_returns_nothing_without_calling_the_provider() -> None:
    provider = _FakeEmbeddingProvider()
    service = _service(provider)
    hits = run(
        service.search(
            "   ", filters=RetrievalFilters(), profile=RetrievalProfile(name="product")
        )
    )
    assert hits == ()
    assert provider.calls == 0


# -- workflow state ------------------------------------------------------


def _run() -> WorkflowRun:
    return WorkflowRun(
        run_id="wf_1",
        steps=[
            WorkflowStep("state", StepKind.TOOL_CALL, "retrieve financial state"),
            WorkflowStep(
                "project",
                StepKind.DETERMINISTIC_CALCULATION,
                "run scenario",
                depends_on=("state",),
            ),
            WorkflowStep(
                "explain",
                StepKind.AGENT_GENERATION,
                "explain the projection",
                depends_on=("project",),
            ),
        ],
    )


def test_workflow_only_offers_steps_whose_dependencies_succeeded() -> None:
    workflow = _run()
    assert [step.step_id for step in workflow.ready_steps()] == ["state"]

    workflow.step("state").status = StepStatus.SUCCEEDED
    assert [step.step_id for step in workflow.ready_steps()] == ["project"]

    workflow.step("project").status = StepStatus.SUCCEEDED
    assert [step.step_id for step in workflow.ready_steps()] == ["explain"]


def test_workflow_state_is_inspectable_and_reports_failure() -> None:
    workflow = _run()
    workflow.step("state").status = StepStatus.SUCCEEDED
    workflow.step("project").status = StepStatus.FAILED
    workflow.step("project").error_code = "TOOL_TIMEOUT"
    workflow.step("explain").status = StepStatus.SKIPPED

    assert workflow.failed is True
    assert workflow.is_complete is True
    assert workflow.ready_steps() == []

    serialized = workflow.to_dict()
    assert serialized["run_id"] == "wf_1"
    assert serialized["steps"][1]["error_code"] == "TOOL_TIMEOUT"


# -- user memory ---------------------------------------------------------


def test_user_memory_is_never_shared_between_users() -> None:
    repository = InMemoryUserMemoryRepository()
    run(
        repository.upsert(
            UserMemory(
                memory_id="mem_1",
                user_id=ALICE,
                kind=MemoryKind.PREFERENCE,
                content="prefers short answers",
            )
        )
    )

    assert len(run(repository.list_for_user(ALICE))) == 1
    assert run(repository.list_for_user(BOB)) == []


def test_user_memory_can_be_filtered_by_kind_and_deleted_by_owner() -> None:
    repository = InMemoryUserMemoryRepository()
    for index, kind in enumerate((MemoryKind.PREFERENCE, MemoryKind.STATED_INTENT)):
        run(
            repository.upsert(
                UserMemory(
                    memory_id=f"mem_{index}",
                    user_id=ALICE,
                    kind=kind,
                    content="something",
                )
            )
        )

    preferences = run(repository.list_for_user(ALICE, kinds=[MemoryKind.PREFERENCE]))
    assert [memory.kind for memory in preferences] == [MemoryKind.PREFERENCE]

    # A different user cannot delete someone else's memory.
    run(repository.delete(BOB, "mem_0"))
    assert len(run(repository.list_for_user(ALICE))) == 2

    run(repository.delete(ALICE, "mem_0"))
    assert len(run(repository.list_for_user(ALICE))) == 1
