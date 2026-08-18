"""The orchestration pipeline.

Fixed stage order, every stage recorded::

    authentication -> authorization -> intent -> risk -> context
    -> agent selection -> tool eligibility -> execution -> validation
    -> response -> telemetry

Design rules this implements:

* the orchestrator is infrastructure — it never answers a question itself;
* routing is deterministic (a lookup table), so obvious requests cost nothing;
* the tool set an agent receives is computed here from the agent spec, the
  caller's permissions and the request's risk ceiling — not from the prompt;
* an intent classified as ``PAYMENT_ACTION`` never reaches an agent
  unconfirmed: it raises a confirmation requirement that the deterministic
  payment flow owns;
* a declared but unimplemented agent fails with ``AGENT_NOT_AVAILABLE`` rather
  than falling back to a generic answer;
* the trace is internal. Only ``text``/``data``/``citations`` reach the user.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Sequence

from libra.ai.agents.contract import AgentRequest, AgentResponse
from libra.ai.agents.registry import AgentRegistry
from libra.ai.context.builder import ContextBuilder
from libra.ai.context.models import ContextSection, ContextSource
from libra.ai.orchestration.intent import IntentClassifier
from libra.ai.orchestration.models import (
    Intent,
    OrchestrationRequest,
    OrchestrationResult,
    Stage,
    TraceEntry,
)
from libra.ai.orchestration.risk import RiskClassifier
from libra.ai.orchestration.routing import AgentRouter
from libra.ai.telemetry.models import AgentRunRecord, ToolInvocationRecord
from libra.ai.telemetry.recorder import TelemetryRecorder
from libra.ai.tools.contract import ToolContext, ToolDefinition
from libra.ai.tools.eligibility import filter_eligible
from libra.ai.tools.registry import ToolRegistry
from libra.core.errors import (
    AgentNotAvailableError,
    ConfirmationRequiredError,
    LibraError,
    PermissionDeniedError,
)
from libra.core.security.principal import Permission

LOGGER = logging.getLogger("libra.ai.orchestrator")


class Orchestrator:
    def __init__(
        self,
        *,
        agents: AgentRegistry,
        tools: ToolRegistry,
        context_builder: ContextBuilder,
        telemetry: TelemetryRecorder,
        intent_classifier: IntentClassifier | None = None,
        risk_classifier: RiskClassifier | None = None,
        router: AgentRouter | None = None,
    ) -> None:
        self._agents = agents
        self._tools = tools
        self._context_builder = context_builder
        self._telemetry = telemetry
        self._intent = intent_classifier or IntentClassifier()
        self._risk = risk_classifier or RiskClassifier()
        self._router = router or AgentRouter()

    async def handle(self, request: OrchestrationRequest) -> OrchestrationResult:
        run_id = f"run_{uuid.uuid4().hex[:16]}"
        started = time.perf_counter()
        trace: list[TraceEntry] = []

        try:
            result = await self._run(run_id, request, trace)
        except LibraError as error:
            await self._record_run(
                run_id,
                request,
                trace,
                agent_id="",
                intent=Intent.UNKNOWN.value,
                risk="unknown",
                prompt_version="",
                latency_ms=(time.perf_counter() - started) * 1000,
                success=False,
                error_code=error.code.value,
            )
            raise

        latency_ms = (time.perf_counter() - started) * 1000
        await self._record_run(
            run_id,
            request,
            trace,
            agent_id=result.agent_id,
            intent=result.intent.value,
            risk=result.risk.value,
            prompt_version=str(result.data.get("prompt_version", "")),
            latency_ms=latency_ms,
            success=True,
            tool_count=len(result.tool_outcomes),
        )
        await self._telemetry.record_tools(
            [
                ToolInvocationRecord(
                    run_id=run_id,
                    tool_name=outcome.tool_name,
                    success=outcome.success,
                    duration_ms=outcome.duration_ms,
                    reason=outcome.reason,
                    error_code=outcome.error_code,
                )
                for outcome in result.tool_outcomes
            ]
        )
        return result

    async def _run(
        self,
        run_id: str,
        request: OrchestrationRequest,
        trace: list[TraceEntry],
    ) -> OrchestrationResult:
        principal = request.principal

        # 1-2. Authentication happened at the HTTP edge; the right to use the
        # assistant at all is checked here, before any model work.
        trace.append(TraceEntry(Stage.AUTHENTICATION, f"principal={principal.user_id}"))
        if not principal.has(Permission.ASSISTANT_USE):
            raise PermissionDeniedError("The assistant is not available for this account.")
        trace.append(TraceEntry(Stage.AUTHORIZATION, "assistant:use granted"))

        # 3. Intent — deterministic rules first.
        intent_decision = self._intent.classify(request.message)
        trace.append(
            TraceEntry(
                Stage.INTENT,
                intent_decision.intent.value,
                data={"matched": intent_decision.matched_phrase},
            )
        )

        # 4. Risk — derived from intent, never from message wording.
        risk = self._risk.assess(intent_decision.intent)
        trace.append(TraceEntry(Stage.RISK, risk.level.value, data={"reason": risk.reason}))

        if risk.requires_confirmation and not request.user_confirmed:
            trace.append(TraceEntry(Stage.VALIDATION, "confirmation required"))
            raise ConfirmationRequiredError(
                "This operation must be confirmed before it can continue."
            )

        # 5. Context — assembled centrally, with provenance per section.
        context = self._context_builder.build(
            principal=principal,
            locale=request.locale,
            sections=self._execution_metadata_sections(run_id, intent_decision.intent),
        )
        trace.append(
            TraceEntry(
                Stage.CONTEXT,
                f"{len(context.sections)} section(s)",
                data={
                    "chars": context.total_chars,
                    "truncated": list(context.truncated_sections),
                },
            )
        )

        # 6. Agent selection — deterministic routing.
        routing = self._router.route(intent_decision.intent)
        spec = self._agents.spec(routing.agent_id)
        trace.append(
            TraceEntry(Stage.AGENT_SELECTION, spec.agent_id, data={"reason": routing.reason})
        )

        # 7. Tool eligibility — computed here, enforced again at execution.
        tool_context = ToolContext(
            principal=principal,
            request_id=request.request_id,
            locale=request.locale,
            conversation_id=request.conversation_id,
            user_confirmed=request.user_confirmed,
        )
        ceiling = min(spec.risk_ceiling, risk.tool_ceiling, key=lambda level: level.rank)
        eligible, denials = filter_eligible(
            self._declared_tools(spec.allowed_tools),
            agent_id=spec.agent_id,
            context=tool_context,
            risk_ceiling=ceiling,
        )
        trace.append(
            TraceEntry(
                Stage.TOOL_ELIGIBILITY,
                f"{len(eligible)} eligible",
                data={
                    "eligible": [item.name for item in eligible],
                    "denied": {item.tool_name: item.reason for item in denials},
                    "ceiling": ceiling.value,
                },
            )
        )

        # 8. Execution — an unimplemented agent fails cleanly and observably.
        if not self._agents.is_implemented(spec.agent_id):
            trace.append(TraceEntry(Stage.EXECUTION, "agent not implemented"))
            raise AgentNotAvailableError("This assistant capability is not available yet.")

        agent = self._agents.agent(spec.agent_id)
        response = await agent.handle(
            AgentRequest(
                message=request.message,
                context=context,
                tool_context=tool_context,
                locale=request.locale,
            )
        )
        trace.append(TraceEntry(Stage.EXECUTION, f"agent={spec.agent_id}"))

        # 9. Validation — an agent may not exceed its declared tool set.
        self._validate(response, allowed_tools=spec.allowed_tools)
        trace.append(TraceEntry(Stage.VALIDATION, "response validated"))

        # 10. Response — user-facing fields only.
        trace.append(TraceEntry(Stage.RESPONSE, f"{len(response.text)} chars"))
        return OrchestrationResult(
            text=response.text,
            agent_id=spec.agent_id,
            intent=intent_decision.intent,
            risk=risk.level,
            conversation_id=request.conversation_id,
            citations=response.citations,
            data={**response.data, "prompt_version": response.prompt_version},
            tool_outcomes=response.tool_outcomes,
            trace=tuple(trace),
            pending_confirmation=response.pending_confirmation,
        )

    def _declared_tools(self, names: frozenset[str]) -> list[ToolDefinition]:
        return [self._tools.get(name) for name in sorted(names) if self._tools.has(name)]

    @staticmethod
    def _validate(response: AgentResponse, *, allowed_tools: frozenset[str]) -> None:
        """Post-execution check: the agent stayed inside its declared contract."""
        used = {outcome.tool_name for outcome in response.tool_outcomes}
        if not used <= allowed_tools:
            raise PermissionDeniedError("The agent used a capability outside its contract.")

    @staticmethod
    def _execution_metadata_sections(run_id: str, intent: Intent) -> Sequence[ContextSection]:
        return (
            ContextSection(
                section_id="execution:run",
                source=ContextSource.EXECUTION_METADATA,
                title="Execution metadata",
                content=f"run_id={run_id}\nintent={intent.value}",
                provenance={"service": "orchestrator"},
                priority=10,
            ),
        )

    async def _record_run(
        self,
        run_id: str,
        request: OrchestrationRequest,
        trace: Sequence[TraceEntry],
        *,
        agent_id: str,
        intent: str,
        risk: str,
        prompt_version: str,
        latency_ms: float,
        success: bool,
        error_code: str | None = None,
        tool_count: int = 0,
    ) -> None:
        await self._telemetry.record_run(
            AgentRunRecord(
                run_id=run_id,
                request_id=request.request_id,
                user_id=request.principal.user_id,
                conversation_id=request.conversation_id,
                agent_id=agent_id,
                intent=intent,
                risk_level=risk,
                prompt_version=prompt_version,
                latency_ms=latency_ms,
                success=success,
                error_code=error_code,
                tool_count=tool_count,
                stages=tuple(entry.stage.value for entry in trace),
            )
        )
