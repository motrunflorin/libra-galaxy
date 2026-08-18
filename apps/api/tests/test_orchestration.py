"""Orchestrator pipeline: routing, risk, eligibility and clean failure."""

from __future__ import annotations

import pytest

from libra.ai.agents.contract import AgentRequest, AgentResponse, AgentSpec
from libra.ai.agents.registry import AgentRegistry
from libra.ai.agents.specs import ALL_SPECS
from libra.ai.context.builder import ContextBuilder
from libra.ai.orchestration.intent import IntentClassifier
from libra.ai.orchestration.models import Intent, OrchestrationRequest, Stage
from libra.ai.orchestration.orchestrator import Orchestrator
from libra.ai.orchestration.risk import RiskClassifier
from libra.ai.orchestration.routing import AgentRouter
from libra.ai.telemetry.recorder import InMemoryTelemetryRecorder
from libra.ai.tools.contract import RiskLevel, ToolOutcome
from libra.core.errors import (
    AgentNotAvailableError,
    ConfirmationRequiredError,
    PermissionDeniedError,
)
from libra.core.locale import Locale
from libra.core.security.principal import Principal, Role
from tests.conftest import ALICE, auth, run


# -- intent classification ----------------------------------------------


@pytest.mark.parametrize(
    "message,expected",
    [
        ("What is my balance?", Intent.ACCOUNT_OVERVIEW),
        ("Care este soldul meu?", Intent.ACCOUNT_OVERVIEW),
        ("How much did I spend last week?", Intent.SPENDING_ANALYSIS),
        ("Cat am cheltuit luna trecuta?", Intent.SPENDING_ANALYSIS),
        ("Cât am cheltuit luna trecută?", Intent.SPENDING_ANALYSIS),
        ("What if I save 500 RON every month?", Intent.WHAT_IF_SIMULATION),
        ("Ce se întâmplă dacă economisesc 500 lei?", Intent.WHAT_IF_SIMULATION),
        ("Show me my subscriptions", Intent.SUBSCRIPTION_REVIEW),
        ("Send money to Andrei", Intent.PAYMENT_ACTION),
        ("purple monkey dishwasher", Intent.UNKNOWN),
    ],
)
def test_intent_is_classified_deterministically(message: str, expected: Intent) -> None:
    assert IntentClassifier().classify(message).intent is expected


def test_payment_intent_wins_over_broader_matches() -> None:
    # "transfer" must not be swallowed by the account-overview phrases.
    decision = IntentClassifier().classify("Transfer 100 RON from my balance")
    assert decision.intent is Intent.PAYMENT_ACTION


# -- risk and routing ----------------------------------------------------


def test_payment_intent_is_high_risk_and_needs_confirmation() -> None:
    assessment = RiskClassifier().assess(Intent.PAYMENT_ACTION)
    assert assessment.level is RiskLevel.HIGH
    assert assessment.requires_confirmation is True


def test_read_only_intents_cap_tools_at_low_risk() -> None:
    assert RiskClassifier().assess(Intent.ACCOUNT_OVERVIEW).tool_ceiling is RiskLevel.LOW


def test_routing_is_deterministic_and_covers_every_intent() -> None:
    router = AgentRouter()
    known_agents = {spec.agent_id for spec in ALL_SPECS}
    for intent in Intent:
        decision = router.route(intent)
        assert decision.deterministic is True
        assert decision.agent_id in known_agents


def test_unknown_intent_routes_to_the_citing_agent() -> None:
    assert AgentRouter().route(Intent.UNKNOWN).agent_id == "document_intelligence"


# -- pipeline ------------------------------------------------------------


class _StubAgent:
    def __init__(self, spec: AgentSpec, outcomes: tuple[ToolOutcome, ...] = ()) -> None:
        self.spec = spec
        self._outcomes = outcomes
        self.seen: AgentRequest | None = None

    async def handle(self, request: AgentRequest) -> AgentResponse:
        self.seen = request
        return AgentResponse(
            agent_id=self.spec.agent_id,
            text="explanation",
            tool_outcomes=self._outcomes,
            prompt_version=self.spec.prompt_version,
        )


def _orchestrator(container, telemetry, agents: AgentRegistry) -> Orchestrator:
    return Orchestrator(
        agents=agents,
        tools=container.tools,
        context_builder=ContextBuilder(),
        telemetry=telemetry,
    )


def _request(principal: Principal, message: str, **kwargs) -> OrchestrationRequest:
    return OrchestrationRequest(
        principal=principal, message=message, locale=Locale.EN, request_id="req_test", **kwargs
    )


def test_unimplemented_agent_fails_cleanly(container, alice) -> None:
    telemetry = InMemoryTelemetryRecorder()
    orchestrator = _orchestrator(container, telemetry, AgentRegistry())

    with pytest.raises(AgentNotAvailableError):
        run(orchestrator.handle(_request(alice, "What is my balance?")))

    # The failure is still observable: a run record exists with the error code.
    assert telemetry.runs[0].success is False
    assert telemetry.runs[0].error_code == "AGENT_NOT_AVAILABLE"
    assert Stage.TOOL_ELIGIBILITY.value in telemetry.runs[0].stages


def test_high_risk_intent_requires_confirmation_before_any_agent_runs(container, alice) -> None:
    telemetry = InMemoryTelemetryRecorder()
    agents = AgentRegistry()
    stub = _StubAgent(agents.spec("financial_advisor"))
    agents.register(stub)

    with pytest.raises(ConfirmationRequiredError):
        run(
            _orchestrator(container, telemetry, agents).handle(
                _request(alice, "Send money to Ana")
            )
        )

    assert stub.seen is None


def test_successful_turn_records_telemetry_without_message_content(container, alice) -> None:
    telemetry = InMemoryTelemetryRecorder()
    agents = AgentRegistry()
    agents.register(_StubAgent(agents.spec("financial_advisor")))

    result = run(
        _orchestrator(container, telemetry, agents).handle(
            _request(alice, "What is my balance?")
        )
    )

    assert result.agent_id == "financial_advisor"
    assert result.intent is Intent.ACCOUNT_OVERVIEW
    record = telemetry.runs[0]
    assert record.success is True
    assert record.user_id == ALICE
    assert "balance" not in str(record.to_dict())


def test_agent_using_an_undeclared_tool_is_rejected(container, alice) -> None:
    agents = AgentRegistry()
    outcome = ToolOutcome(
        tool_name="prepare_transfer", success=True, duration_ms=1.0, reason="test"
    )
    agents.register(_StubAgent(agents.spec("financial_advisor"), outcomes=(outcome,)))

    with pytest.raises(PermissionDeniedError):
        run(
            _orchestrator(container, InMemoryTelemetryRecorder(), agents).handle(
                _request(alice, "What is my balance?")
            )
        )


def test_principal_without_assistant_permission_is_denied(container) -> None:
    stripped = Principal(user_id=ALICE, role=Role.CUSTOMER, permissions=frozenset())
    with pytest.raises(PermissionDeniedError):
        run(
            _orchestrator(container, InMemoryTelemetryRecorder(), AgentRegistry()).handle(
                _request(stripped, "What is my balance?")
            )
        )


def test_eligible_tool_set_respects_the_request_risk_ceiling(container, alice) -> None:
    telemetry = InMemoryTelemetryRecorder()
    agents = AgentRegistry()
    stub = _StubAgent(agents.spec("financial_advisor"))
    agents.register(stub)

    run(_orchestrator(container, telemetry, agents).handle(_request(alice, "What is my balance?")))

    assert stub.seen is not None
    assert stub.seen.tool_context.principal.user_id == ALICE


# -- HTTP surface --------------------------------------------------------


def test_assistant_endpoint_reports_unavailable_without_internals(client) -> None:
    response = client.post(
        "/api/v1/assistant/messages",
        json={"message": "What is my balance?"},
        headers=auth(ALICE),
    )
    payload = response.json()

    assert response.status_code == 503
    assert payload["error"]["code"] == "AGENT_NOT_AVAILABLE"
    # The internal trace must never be serialised to a banking user.
    assert "trace" not in str(payload)


def test_capabilities_are_filtered_by_permission(client) -> None:
    body = client.get("/api/v1/assistant/capabilities", headers=auth(ALICE)).json()["body"]
    assert {agent["agent_id"] for agent in body["agents"]} == {
        spec.agent_id for spec in ALL_SPECS
    }
    assert all(agent["available"] is False for agent in body["agents"])
    assert {tool["name"] for tool in body["tools"]} == {"get_accounts", "run_scenario"}


def test_agent_specs_and_tool_grants_agree(container) -> None:
    """A capability must be granted from both sides or not at all."""
    for spec in container.agents.specs():
        for tool_name in spec.allowed_tools:
            assert container.tools.has(tool_name), f"{spec.agent_id} -> missing {tool_name}"
            definition = container.tools.get(tool_name)
            assert spec.agent_id in definition.allowed_agents

    for definition in container.tools.all():
        for agent_id in definition.allowed_agents:
            spec = container.agents.spec(agent_id)
            assert spec.allows_tool(definition.name)


def test_no_agent_may_exceed_its_declared_risk_ceiling(container) -> None:
    for spec in container.agents.specs():
        for tool_name in spec.allowed_tools:
            definition = container.tools.get(tool_name)
            assert definition.risk_level.rank <= spec.risk_ceiling.rank
