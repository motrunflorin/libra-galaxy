"""Agent registry.

Holds the declared specifications and, once implemented, the agent instances.
An agent that is declared but not implemented is not an error: the
orchestrator routes to it and fails with ``AGENT_NOT_AVAILABLE``, which is
observable and honest, instead of silently answering with a generic model.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from libra.ai.agents.contract import Agent, AgentSpec
from libra.ai.agents.specs import ALL_SPECS
from libra.core.errors import AgentNotAvailableError


class AgentRegistry:
    def __init__(
        self,
        specs: Iterable[AgentSpec] = ALL_SPECS,
        agents: Iterable[Agent] = (),
    ) -> None:
        self._specs: dict[str, AgentSpec] = {spec.agent_id: spec for spec in specs}
        self._agents: dict[str, Agent] = {}
        for agent in agents:
            self.register(agent)

    def register(self, agent: Agent) -> None:
        if agent.spec.agent_id not in self._specs:
            raise ValueError(f"Unknown agent id: {agent.spec.agent_id!r}")
        self._agents[agent.spec.agent_id] = agent

    def spec(self, agent_id: str) -> AgentSpec:
        spec = self._specs.get(agent_id)
        if spec is None:
            raise AgentNotAvailableError()
        return spec

    def specs(self) -> Sequence[AgentSpec]:
        return tuple(self._specs.values())

    def is_implemented(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def agent(self, agent_id: str) -> Agent:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise AgentNotAvailableError(
                "This assistant capability is not available yet."
            )
        return agent
