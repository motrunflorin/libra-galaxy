"""Context builder.

One place assembles context for every agent. Agents cannot reach into
conversations, memory or retrieval on their own — they receive an
:class:`AssembledContext` and nothing else.

Assembly rules:

* sections are added in a fixed order, so prompts are reproducible;
* each source has its own character budget, so conversation history can never
  displace authoritative banking figures;
* when a section must be shortened it is truncated at the end and recorded in
  ``truncated_sections`` rather than silently dropped.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from libra.ai.context.models import (
    AssembledContext,
    ContextBudget,
    ContextSection,
    ContextSource,
)
from libra.core.locale import Locale
from libra.core.security.principal import Principal

#: Fixed assembly order. Authoritative sources come last so they sit closest
#: to the user's question in the rendered prompt.
_ORDER: tuple[ContextSource, ...] = (
    ContextSource.IDENTITY,
    ContextSource.PERMISSIONS,
    ContextSource.LOCALE,
    ContextSource.CONVERSATION_SUMMARY,
    ContextSource.USER_MEMORY,
    ContextSource.RECENT_CONVERSATION,
    ContextSource.RETRIEVED_KNOWLEDGE,
    ContextSource.BANKING_STATE,
    ContextSource.TOOL_RESULT,
    ContextSource.EXECUTION_METADATA,
)


class ContextBuilder:
    def __init__(self, budget: ContextBudget | None = None) -> None:
        self._budget = budget or ContextBudget()

    def build(
        self,
        *,
        principal: Principal,
        locale: Locale,
        sections: Iterable[ContextSection] = (),
    ) -> AssembledContext:
        collected = list(self._base_sections(principal, locale))
        collected.extend(sections)
        return self._assemble(collected)

    @staticmethod
    def _base_sections(principal: Principal, locale: Locale) -> Sequence[ContextSection]:
        """Identity, permissions and locale are always present.

        The model is told *which* rights the caller holds so it can explain
        why something is unavailable — the rights themselves are enforced in
        the tool layer, never by the model.
        """
        return (
            ContextSection(
                section_id="identity:principal",
                source=ContextSource.IDENTITY,
                title="Authenticated user",
                content=f"user_id={principal.user_id}\nrole={principal.role.value}",
                provenance={"service": "authentication"},
                priority=100,
            ),
            ContextSection(
                section_id="permissions:granted",
                source=ContextSource.PERMISSIONS,
                title="Granted permissions",
                content="\n".join(sorted(item.value for item in principal.permissions)),
                provenance={"service": "authorization"},
                priority=100,
            ),
            ContextSection(
                section_id="locale:active",
                source=ContextSource.LOCALE,
                title="Response language",
                content=f"Answer in: {locale.value}",
                provenance={"service": "locale"},
                priority=100,
            ),
        )

    def _assemble(self, sections: Sequence[ContextSection]) -> AssembledContext:
        ordered = sorted(
            sections,
            key=lambda section: (_ORDER.index(section.source), -section.priority),
        )

        used_per_source: dict[ContextSource, int] = {}
        used_total = 0
        kept: list[ContextSection] = []
        truncated: list[str] = []

        for section in ordered:
            source_used = used_per_source.get(section.source, 0)
            source_room = self._budget.limit_for(section.source) - source_used
            total_room = self._budget.total_chars - used_total
            room = min(source_room, total_room)

            if room <= 0:
                truncated.append(section.section_id)
                continue

            if section.size > room:
                kept.append(
                    ContextSection(
                        section_id=section.section_id,
                        source=section.source,
                        title=section.title,
                        content=section.content[:room],
                        provenance={**section.provenance, "truncated": True},
                        priority=section.priority,
                    )
                )
                truncated.append(section.section_id)
                used_per_source[section.source] = source_used + room
                used_total += room
                continue

            kept.append(section)
            used_per_source[section.source] = source_used + section.size
            used_total += section.size

        return AssembledContext(sections=tuple(kept), truncated_sections=tuple(truncated))
