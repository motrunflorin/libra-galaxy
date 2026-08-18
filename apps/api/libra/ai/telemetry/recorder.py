"""Telemetry sinks.

``TelemetryRecorder`` is the seam between the orchestrator and wherever
observability data lands (Mongo collections today, an APM exporter later).
The in-memory implementation backs tests and local development.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Sequence

from libra.ai.telemetry.models import AgentRunRecord, ToolInvocationRecord, UsageRecord
from libra.core.logging import log_event

LOGGER = logging.getLogger("libra.ai.telemetry")


class TelemetryRecorder(ABC):
    @abstractmethod
    async def record_run(self, record: AgentRunRecord) -> None: ...

    @abstractmethod
    async def record_tools(self, records: Sequence[ToolInvocationRecord]) -> None: ...

    @abstractmethod
    async def record_usage(self, record: UsageRecord) -> None: ...


class LoggingTelemetryRecorder(TelemetryRecorder):
    """Writes structured log events. Default for local development."""

    async def record_run(self, record: AgentRunRecord) -> None:
        log_event(LOGGER, "agent.run", **record.to_dict())

    async def record_tools(self, records: Sequence[ToolInvocationRecord]) -> None:
        for item in records:
            log_event(
                LOGGER,
                "agent.tool",
                run_id=item.run_id,
                tool=item.tool_name,
                success=item.success,
                duration_ms=round(item.duration_ms, 2),
                error_code=item.error_code,
            )

    async def record_usage(self, record: UsageRecord) -> None:
        log_event(
            LOGGER,
            "ai.usage",
            run_id=record.run_id,
            deployment=record.deployment,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            estimated_cost_usd=round(record.estimated_cost_usd, 8),
            feature=record.feature,
            agent_id=record.agent_id,
        )


class InMemoryTelemetryRecorder(TelemetryRecorder):
    """Collects records so tests can assert what was observed."""

    def __init__(self) -> None:
        self.runs: list[AgentRunRecord] = []
        self.tools: list[ToolInvocationRecord] = []
        self.usage: list[UsageRecord] = []

    async def record_run(self, record: AgentRunRecord) -> None:
        self.runs.append(record)

    async def record_tools(self, records: Sequence[ToolInvocationRecord]) -> None:
        self.tools.extend(records)

    async def record_usage(self, record: UsageRecord) -> None:
        self.usage.append(record)
