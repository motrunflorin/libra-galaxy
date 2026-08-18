"""Tool eligibility and execution — the agent-to-bank boundary."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel

from libra.ai.tools.contract import (
    RiskLevel,
    SideEffect,
    ToolCall,
    ToolContext,
    ToolDefinition,
)
from libra.ai.tools.eligibility import (
    AGENT_NOT_ALLOWED,
    CONFIRMATION_REQUIRED,
    MISSING_PERMISSION,
    RISK_CEILING_EXCEEDED,
    evaluate,
)
from libra.ai.tools.executor import ToolExecutor
from libra.ai.tools.registry import ToolRegistry
from libra.core.errors import ToolNotEligibleError
from libra.core.security.principal import Permission
from tests.conftest import ALICE, principal_for, run


class _Input(BaseModel):
    value: int = 0


class _Output(BaseModel):
    value: int


def _tool(
    name: str,
    *,
    agents: set[str] = {"financial_advisor"},
    permissions: set[Permission] = set(),
    side_effect: SideEffect = SideEffect.READ_ONLY,
    risk: RiskLevel = RiskLevel.LOW,
    confirm: bool = False,
    delay: float = 0.0,
) -> ToolDefinition:
    async def handler(context: ToolContext, arguments: _Input) -> _Output:
        if delay:
            await asyncio.sleep(delay)
        return _Output(value=arguments.value * 2)

    return ToolDefinition(
        name=name,
        description=name,
        input_model=_Input,
        output_model=_Output,
        handler=handler,
        allowed_agents=frozenset(agents),
        required_permissions=frozenset(permissions),
        side_effect=side_effect,
        risk_level=risk,
        requires_confirmation=confirm,
    )


def _context(*, confirmed: bool = False, permissions: set[Permission] | None = None) -> ToolContext:
    principal = principal_for(ALICE)
    if permissions is not None:
        principal = type(principal)(
            user_id=principal.user_id,
            role=principal.role,
            permissions=frozenset(permissions),
        )
    return ToolContext(principal=principal, request_id="req_test", user_confirmed=confirmed)


# -- eligibility ---------------------------------------------------------


def test_agent_outside_allowed_set_is_denied() -> None:
    decision = evaluate(_tool("t"), agent_id="engagement", context=_context())
    assert decision.allowed is False
    assert decision.reason == AGENT_NOT_ALLOWED


def test_missing_permission_is_denied() -> None:
    definition = _tool("t", permissions={Permission.PAYMENTS_EXECUTE})
    decision = evaluate(
        definition, agent_id="financial_advisor", context=_context(permissions=set())
    )
    assert decision.reason == MISSING_PERMISSION


def test_risk_ceiling_caps_high_risk_tools() -> None:
    definition = _tool("t", risk=RiskLevel.HIGH, side_effect=SideEffect.PREPARES_MUTATION)
    decision = evaluate(
        definition,
        agent_id="financial_advisor",
        context=_context(),
        risk_ceiling=RiskLevel.LOW,
    )
    assert decision.reason == RISK_CEILING_EXCEEDED


def test_confirmation_is_required_before_execution() -> None:
    definition = _tool("t", confirm=True, side_effect=SideEffect.PREPARES_MUTATION)
    denied = evaluate(definition, agent_id="financial_advisor", context=_context())
    allowed = evaluate(
        definition, agent_id="financial_advisor", context=_context(confirmed=True)
    )
    assert denied.reason == CONFIRMATION_REQUIRED
    assert allowed.allowed is True


def test_mutating_tool_must_declare_confirmation() -> None:
    with pytest.raises(ValueError):
        _tool("bad", side_effect=SideEffect.MUTATES, confirm=False)


# -- execution -----------------------------------------------------------


def test_executor_validates_arguments_against_the_schema() -> None:
    registry = ToolRegistry([_tool("t")])
    executor = ToolExecutor(registry)
    outcome = run(
        executor.execute(
            ToolCall("t", {"value": "not-an-int"}),
            agent_id="financial_advisor",
            context=_context(),
        )
    )
    assert outcome.success is False
    assert outcome.error_code == "VALIDATION_ERROR"


def test_executor_rechecks_eligibility_before_running() -> None:
    registry = ToolRegistry([_tool("t", agents={"engagement"})])
    outcome = run(
        ToolExecutor(registry).execute(
            ToolCall("t"), agent_id="financial_advisor", context=_context()
        )
    )
    assert outcome.error_code == "TOOL_NOT_ELIGIBLE"


def test_unknown_tool_name_is_not_eligible() -> None:
    registry = ToolRegistry([])
    with pytest.raises(ToolNotEligibleError):
        registry.get("does_not_exist")


def test_timeout_is_reported_not_raised() -> None:
    registry = ToolRegistry([_tool("slow", delay=0.2)])
    executor = ToolExecutor(registry, default_timeout_seconds=1.0)
    definition = registry.get("slow")
    object.__setattr__(definition, "timeout_seconds", 0.01)

    outcome = run(
        executor.execute(ToolCall("slow"), agent_id="financial_advisor", context=_context())
    )
    assert outcome.success is False
    assert outcome.error_code == "TOOL_TIMEOUT"


def test_read_only_tools_run_concurrently() -> None:
    registry = ToolRegistry(
        [_tool("a", delay=0.15), _tool("b", delay=0.15), _tool("c", delay=0.15)]
    )
    executor = ToolExecutor(registry)

    async def measure() -> float:
        loop = asyncio.get_running_loop()
        started = loop.time()
        await executor.execute_many(
            [ToolCall("a"), ToolCall("b"), ToolCall("c")],
            agent_id="financial_advisor",
            context=_context(),
        )
        return loop.time() - started

    # Sequential execution would take ~0.45s; concurrent stays near 0.15s.
    assert run(measure()) < 0.35


def test_mutations_are_never_run_in_parallel() -> None:
    order: list[str] = []

    async def make(name: str, delay: float):
        async def handler(context: ToolContext, arguments: _Input) -> _Output:
            await asyncio.sleep(delay)
            order.append(name)
            return _Output(value=1)

        return handler

    async def build() -> ToolRegistry:
        read = _tool("read", delay=0.1)
        mutate = ToolDefinition(
            name="mutate",
            description="mutate",
            input_model=_Input,
            output_model=_Output,
            handler=await make("mutate", 0.0),
            allowed_agents=frozenset({"financial_advisor"}),
            side_effect=SideEffect.MUTATES,
            risk_level=RiskLevel.LOW,
            requires_confirmation=True,
        )
        object.__setattr__(read, "handler", await make("read", 0.1))
        return ToolRegistry([read, mutate])

    async def scenario() -> list[str]:
        registry = await build()
        await ToolExecutor(registry).execute_many(
            [ToolCall("read"), ToolCall("mutate")],
            agent_id="financial_advisor",
            context=_context(confirmed=True),
        )
        return order

    # The slow read finishes before the mutation starts: the mutation is a
    # barrier, so nothing is executed speculatively alongside it.
    assert run(scenario()) == ["read", "mutate"]


def test_registered_banking_tools_expose_full_metadata(container) -> None:
    metadata = {item["name"]: item for item in container.tools.metadata()}
    accounts = metadata["get_accounts"]

    assert accounts["required_permissions"] == ["accounts:read"]
    assert accounts["side_effect"] == "read_only"
    assert accounts["parallel_safe"] is True
    assert "properties" in accounts["input_schema"]


def test_get_accounts_tool_returns_only_the_callers_accounts(container) -> None:
    definition = container.tools.get("get_accounts")
    outcome = run(
        ToolExecutor(container.tools).execute(
            ToolCall("get_accounts", {"include_subaccounts": True}),
            agent_id="financial_advisor",
            context=_context(permissions={Permission.ACCOUNTS_READ}),
        )
    )

    assert definition.is_parallel_safe
    assert outcome.success is True
    assert [account["account_id"] for account in outcome.output["accounts"]] == [
        "acc_alice_current"
    ]
    # The tool masks the IBAN: an agent never needs the full number.
    assert outcome.output["accounts"][0]["iban_suffix"] == "0000"
