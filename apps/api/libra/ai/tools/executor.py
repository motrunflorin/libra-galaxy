"""Tool execution.

Improvements over the reference project's executor, driven by banking needs:

* eligibility is re-checked immediately before execution, so a plan built
  earlier in the turn cannot smuggle in a tool the caller may not use;
* arguments are validated against the declared input model, and results
  against the output model — an agent cannot pass free-form data to a service;
* only ``read_only``/``compute`` tools run concurrently; anything that
  prepares or performs a mutation runs sequentially, never speculatively;
* every execution produces a ``ToolOutcome`` for telemetry, including failures.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Sequence

from pydantic import ValidationError as PydanticValidationError

from libra.ai.tools.contract import RiskLevel, ToolCall, ToolContext, ToolOutcome
from libra.ai.tools.eligibility import evaluate
from libra.ai.tools.registry import ToolRegistry
from libra.core.errors import ErrorCode, LibraError
from libra.core.logging import log_event

LOGGER = logging.getLogger("libra.ai.tools")


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, *, default_timeout_seconds: float = 15.0) -> None:
        self._registry = registry
        self._default_timeout = max(1.0, default_timeout_seconds)

    async def execute(
        self,
        call: ToolCall,
        *,
        agent_id: str,
        context: ToolContext,
        risk_ceiling: RiskLevel = RiskLevel.HIGH,
    ) -> ToolOutcome:
        started = time.perf_counter()

        try:
            definition = self._registry.get(call.tool_name)
        except LibraError as error:
            return self._failure(call, error, started)

        decision = evaluate(
            definition, agent_id=agent_id, context=context, risk_ceiling=risk_ceiling
        )
        if not decision.allowed:
            return ToolOutcome(
                tool_name=call.tool_name,
                success=False,
                duration_ms=self._elapsed(started),
                reason=call.reason,
                error_code=ErrorCode.TOOL_NOT_ELIGIBLE.value,
                error_message=decision.reason,
            )

        try:
            arguments = definition.input_model.model_validate(call.arguments)
        except PydanticValidationError:
            return ToolOutcome(
                tool_name=call.tool_name,
                success=False,
                duration_ms=self._elapsed(started),
                reason=call.reason,
                error_code=ErrorCode.VALIDATION_ERROR.value,
                error_message="The tool arguments did not match the declared schema.",
            )

        timeout = definition.timeout_seconds or self._default_timeout
        try:
            result = await asyncio.wait_for(
                definition.handler(context, arguments), timeout=timeout
            )
            output = definition.output_model.model_validate(result).model_dump(mode="json")
        except asyncio.TimeoutError:
            return ToolOutcome(
                tool_name=call.tool_name,
                success=False,
                duration_ms=self._elapsed(started),
                reason=call.reason,
                error_code=ErrorCode.TOOL_TIMEOUT.value,
                error_message=f"The tool exceeded its {timeout:.0f}s budget.",
            )
        except LibraError as error:
            return self._failure(call, error, started)
        except Exception:  # noqa: BLE001 - unexpected tool bug
            LOGGER.exception(
                "tool.unexpected_error", extra={"event_data": {"tool": call.tool_name}}
            )
            return ToolOutcome(
                tool_name=call.tool_name,
                success=False,
                duration_ms=self._elapsed(started),
                reason=call.reason,
                error_code=ErrorCode.TOOL_EXECUTION_ERROR.value,
                error_message="The tool failed to execute.",
            )

        outcome = ToolOutcome(
            tool_name=call.tool_name,
            success=True,
            duration_ms=self._elapsed(started),
            reason=call.reason,
            output=output,
        )
        log_event(
            LOGGER,
            "tool.executed",
            tool=outcome.tool_name,
            agent=agent_id,
            success=True,
            duration_ms=round(outcome.duration_ms, 2),
        )
        return outcome

    async def execute_many(
        self,
        calls: Sequence[ToolCall],
        *,
        agent_id: str,
        context: ToolContext,
        risk_ceiling: RiskLevel = RiskLevel.HIGH,
    ) -> list[ToolOutcome]:
        """Run a batch, parallelising only what is safe to parallelise.

        Order of results always matches the order of ``calls`` so a workflow
        step can rely on positions.
        """
        if not calls:
            return []

        outcomes: list[ToolOutcome | None] = [None] * len(calls)
        parallel_batch: list[tuple[int, ToolCall]] = []

        async def flush() -> None:
            if not parallel_batch:
                return
            results = await asyncio.gather(
                *(
                    self.execute(
                        call, agent_id=agent_id, context=context, risk_ceiling=risk_ceiling
                    )
                    for _, call in parallel_batch
                )
            )
            for (index, _), result in zip(parallel_batch, results):
                outcomes[index] = result
            parallel_batch.clear()

        for index, call in enumerate(calls):
            if self._is_parallel_safe(call):
                parallel_batch.append((index, call))
                continue
            # A mutation acts as a barrier: everything queued before it
            # completes first, then it runs alone.
            await flush()
            outcomes[index] = await self.execute(
                call, agent_id=agent_id, context=context, risk_ceiling=risk_ceiling
            )

        await flush()
        return [outcome for outcome in outcomes if outcome is not None]

    def _is_parallel_safe(self, call: ToolCall) -> bool:
        if not self._registry.has(call.tool_name):
            # Unknown tools are rejected by execute(); treat them as safe to
            # batch so the rejection does not act as a barrier.
            return True
        return self._registry.get(call.tool_name).is_parallel_safe

    @staticmethod
    def _elapsed(started: float) -> float:
        return (time.perf_counter() - started) * 1000

    def _failure(self, call: ToolCall, error: LibraError, started: float) -> ToolOutcome:
        return ToolOutcome(
            tool_name=call.tool_name,
            success=False,
            duration_ms=self._elapsed(started),
            reason=call.reason,
            error_code=error.code.value,
            error_message=error.message,
        )
