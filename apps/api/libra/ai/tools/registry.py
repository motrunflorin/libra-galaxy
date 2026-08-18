"""Tool registry.

An instance, not a module-level global: the composition root builds one and
injects it, so tests can register fakes without touching process state. (The
reference project used import-time singletons; that made its tool layer
impossible to test in isolation.)
"""

from __future__ import annotations

from typing import Iterable, Sequence

from libra.ai.tools.contract import ToolDefinition
from libra.core.errors import ToolNotEligibleError


class ToolRegistry:
    def __init__(self, definitions: Iterable[ToolDefinition] = ()) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ValueError(f"Tool {definition.name!r} is already registered.")
        self._tools[definition.name] = definition

    def get(self, name: str) -> ToolDefinition:
        definition = self._tools.get(name)
        if definition is None:
            # Unknown names are an eligibility failure, not a 404: a model may
            # hallucinate a tool name and must not learn what exists.
            raise ToolNotEligibleError()
        return definition

    def has(self, name: str) -> bool:
        return name in self._tools

    def all(self) -> Sequence[ToolDefinition]:
        return tuple(self._tools.values())

    def for_agent(self, agent_id: str) -> Sequence[ToolDefinition]:
        return tuple(
            definition
            for definition in self._tools.values()
            if agent_id in definition.allowed_agents
        )

    def metadata(self) -> list[dict[str, object]]:
        return [definition.public_metadata() for definition in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)
