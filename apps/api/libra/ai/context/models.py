"""Context sections and provenance.

Every piece of text that reaches a model is tagged with where it came from.
Provenance is what keeps the four sources separable at review time::

    authoritative banking state   <- tools -> deterministic services
    conversation memory           <- the user's own past messages
    retrieved knowledge           <- RAG over unstructured documents
    model output                  <- never re-used as fact

A section that carries banking figures must have
``source=ContextSource.BANKING_STATE``; nothing else is allowed to be treated
as authoritative downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ContextSource(str, Enum):
    IDENTITY = "identity"
    PERMISSIONS = "permissions"
    LOCALE = "locale"
    RECENT_CONVERSATION = "recent_conversation"
    CONVERSATION_SUMMARY = "conversation_summary"
    USER_MEMORY = "user_memory"
    RETRIEVED_KNOWLEDGE = "retrieved_knowledge"
    BANKING_STATE = "banking_state"
    TOOL_RESULT = "tool_result"
    EXECUTION_METADATA = "execution_metadata"

    @property
    def is_authoritative(self) -> bool:
        """Only deterministic services produce authoritative figures."""
        return self in (ContextSource.BANKING_STATE, ContextSource.TOOL_RESULT)


@dataclass(frozen=True)
class ContextSection:
    """One labelled block of context."""

    #: Stable identifier an agent can cite, e.g. ``banking_state:accounts``.
    section_id: str
    source: ContextSource
    title: str
    content: str
    #: Where the content came from: service name, document id, message range.
    provenance: dict[str, Any] = field(default_factory=dict)
    #: Higher priority survives truncation. 100 = never drop.
    priority: int = 50

    @property
    def size(self) -> int:
        return len(self.content)


@dataclass(frozen=True)
class ContextBudget:
    """Character budgets per source.

    Budgets are per-source rather than global so that a long conversation can
    never crowd out authoritative banking figures.
    """

    total_chars: int = 24_000
    per_source: dict[ContextSource, int] = field(
        default_factory=lambda: {
            ContextSource.IDENTITY: 500,
            ContextSource.PERMISSIONS: 500,
            ContextSource.LOCALE: 200,
            ContextSource.RECENT_CONVERSATION: 6_000,
            ContextSource.CONVERSATION_SUMMARY: 3_000,
            ContextSource.USER_MEMORY: 2_000,
            ContextSource.RETRIEVED_KNOWLEDGE: 7_000,
            ContextSource.BANKING_STATE: 6_000,
            ContextSource.TOOL_RESULT: 5_000,
            ContextSource.EXECUTION_METADATA: 500,
        }
    )

    def limit_for(self, source: ContextSource) -> int:
        return self.per_source.get(source, 1_000)


@dataclass(frozen=True)
class AssembledContext:
    """The finished context handed to an agent."""

    sections: tuple[ContextSection, ...]
    #: Sections dropped or shortened, for telemetry and debugging.
    truncated_sections: tuple[str, ...] = ()

    def by_source(self, source: ContextSource) -> tuple[ContextSection, ...]:
        return tuple(section for section in self.sections if section.source is source)

    def authoritative_sections(self) -> tuple[ContextSection, ...]:
        return tuple(section for section in self.sections if section.source.is_authoritative)

    @property
    def total_chars(self) -> int:
        return sum(section.size for section in self.sections)

    def render(self) -> str:
        """Render as a labelled prompt block.

        Labels are part of the safety design: the model is told which block is
        authoritative and which is recollection.
        """
        blocks = [
            f"## {section.title}\n[source={section.source.value} id={section.section_id}]\n"
            f"{section.content}"
            for section in self.sections
        ]
        return "\n\n---\n\n".join(blocks)
