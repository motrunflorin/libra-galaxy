"""Context assembly: fixed order, per-source budgets, visible provenance."""

from __future__ import annotations

from libra.ai.context.builder import ContextBuilder
from libra.ai.context.models import ContextBudget, ContextSection, ContextSource
from libra.core.locale import Locale
from tests.conftest import ALICE, principal_for


def _section(source: ContextSource, size: int = 10, section_id: str = "s") -> ContextSection:
    return ContextSection(
        section_id=section_id,
        source=source,
        title=source.value,
        content="x" * size,
        provenance={"service": "test"},
    )


def test_identity_permissions_and_locale_are_always_present() -> None:
    context = ContextBuilder().build(principal=principal_for(ALICE), locale=Locale.RO)
    sources = {section.source for section in context.sections}

    assert ContextSource.IDENTITY in sources
    assert ContextSource.PERMISSIONS in sources
    assert "Answer in: ro" in context.render()


def test_sections_are_ordered_so_banking_state_sits_closest_to_the_question() -> None:
    context = ContextBuilder().build(
        principal=principal_for(ALICE),
        locale=Locale.EN,
        sections=[
            _section(ContextSource.BANKING_STATE, section_id="banking"),
            _section(ContextSource.RECENT_CONVERSATION, section_id="recent"),
            _section(ContextSource.RETRIEVED_KNOWLEDGE, section_id="knowledge"),
        ],
    )
    order = [section.section_id for section in context.sections]

    assert order.index("recent") < order.index("knowledge") < order.index("banking")


def test_conversation_history_cannot_crowd_out_banking_state() -> None:
    budget = ContextBudget(
        total_chars=1_000,
        per_source={
            ContextSource.IDENTITY: 100,
            ContextSource.PERMISSIONS: 100,
            ContextSource.LOCALE: 50,
            ContextSource.RECENT_CONVERSATION: 200,
            ContextSource.BANKING_STATE: 400,
        },
    )
    context = ContextBuilder(budget).build(
        principal=principal_for(ALICE),
        locale=Locale.EN,
        sections=[
            _section(ContextSource.RECENT_CONVERSATION, size=5_000, section_id="recent"),
            _section(ContextSource.BANKING_STATE, size=300, section_id="banking"),
        ],
    )
    banking = context.by_source(ContextSource.BANKING_STATE)

    assert len(banking) == 1
    assert banking[0].size == 300
    assert "recent" in context.truncated_sections


def test_truncation_is_recorded_not_silent() -> None:
    budget = ContextBudget(total_chars=10_000, per_source={ContextSource.USER_MEMORY: 20})
    context = ContextBuilder(budget).build(
        principal=principal_for(ALICE),
        locale=Locale.EN,
        sections=[_section(ContextSource.USER_MEMORY, size=100, section_id="memory")],
    )
    memory = context.by_source(ContextSource.USER_MEMORY)[0]

    assert memory.size == 20
    assert memory.provenance["truncated"] is True
    assert "memory" in context.truncated_sections


def test_memory_is_never_marked_authoritative() -> None:
    context = ContextBuilder().build(
        principal=principal_for(ALICE),
        locale=Locale.EN,
        sections=[
            _section(ContextSource.USER_MEMORY, section_id="memory"),
            _section(ContextSource.RETRIEVED_KNOWLEDGE, section_id="knowledge"),
            _section(ContextSource.BANKING_STATE, section_id="banking"),
        ],
    )
    authoritative = {section.section_id for section in context.authoritative_sections()}

    assert authoritative == {"banking"}
    assert ContextSource.USER_MEMORY.is_authoritative is False
    assert ContextSource.RETRIEVED_KNOWLEDGE.is_authoritative is False


def test_rendered_prompt_labels_every_source() -> None:
    rendered = (
        ContextBuilder()
        .build(
            principal=principal_for(ALICE),
            locale=Locale.EN,
            sections=[_section(ContextSource.BANKING_STATE, section_id="banking")],
        )
        .render()
    )
    assert "[source=banking_state id=banking]" in rendered
