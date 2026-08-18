"""Conversation ownership and incremental compression."""

from __future__ import annotations

import pytest

from libra.ai.conversations.models import MessageRole
from libra.core.errors import ResourceNotFoundError
from libra.core.locale import Locale
from tests.conftest import run


def _talk(container, principal, conversation_id: str, turns: int) -> None:
    for index in range(turns):
        run(
            container.conversations.append(
                principal,
                conversation_id,
                role=MessageRole.USER,
                content=f"question number {index} about my budget",
            )
        )
        run(
            container.conversations.append(
                principal,
                conversation_id,
                role=MessageRole.ASSISTANT,
                content=f"answer number {index}",
                agent_id="financial_advisor",
            )
        )


def test_conversations_are_owned_by_one_user(container, alice, bob) -> None:
    conversation = run(container.conversations.start(alice, locale=Locale.RO))

    with pytest.raises(ResourceNotFoundError):
        run(container.conversations.get(bob, conversation.conversation_id))


def test_recent_window_stays_bounded(container, alice) -> None:
    conversation = run(container.conversations.start(alice, locale=Locale.EN))
    _talk(container, alice, conversation.conversation_id, turns=20)

    recent = run(
        container.conversations.recent_messages(alice, conversation.conversation_id, limit=12)
    )
    assert len(recent) == 12


def test_older_turns_are_folded_into_a_summary(container, alice) -> None:
    conversation = run(container.conversations.start(alice, locale=Locale.EN))
    _talk(container, alice, conversation.conversation_id, turns=15)

    summary = run(container.conversations.compress(alice, conversation.conversation_id))

    assert summary is not None
    assert summary.covers_up_to_sequence > 0
    assert "question number 0" in summary.content
    # The most recent turns stay verbatim rather than being summarised.
    assert "question number 14" not in summary.content


def test_compression_is_incremental(container, alice) -> None:
    conversation = run(container.conversations.start(alice, locale=Locale.EN))
    _talk(container, alice, conversation.conversation_id, turns=15)
    first = run(container.conversations.compress(alice, conversation.conversation_id))

    _talk(container, alice, conversation.conversation_id, turns=5)
    second = run(container.conversations.compress(alice, conversation.conversation_id))

    assert first is not None and second is not None
    assert second.covers_up_to_sequence > first.covers_up_to_sequence
    # Earlier content is preserved, not recomputed from scratch.
    assert second.content.startswith(first.content[:50])


def test_summary_is_length_capped(container, alice) -> None:
    conversation = run(container.conversations.start(alice, locale=Locale.EN))
    _talk(container, alice, conversation.conversation_id, turns=200)

    summary = run(container.conversations.compress(alice, conversation.conversation_id))

    assert summary is not None
    assert len(summary.content) <= 3_000


def test_memory_is_not_banking_state() -> None:
    from libra.ai.memory.models import MemoryKind, UserMemory

    memory = UserMemory(
        memory_id="mem_1",
        user_id="usr_alice",
        kind=MemoryKind.STATED_INTENT,
        content="wants to save 500 RON monthly",
    )
    assert memory.is_authoritative_banking_state is False
