"""``run_scenario`` — deterministic CashPlay projection.

The engine computes; the Financial Advisor agent explains. The tool is
``compute``: it reads no state and writes none, so it is safe to run in
parallel with reads.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from libra.ai.tools.contract import RiskLevel, SideEffect, ToolContext, ToolDefinition
from libra.core.money import Money
from libra.core.security.principal import Permission
from libra.domains.scenarios.models import ChangeKind, ScenarioChange, ScenarioInput
from libra.domains.scenarios.service import ScenarioService

TOOL_NAME = "run_scenario"


class ScenarioChangeInput(BaseModel):
    change_id: str
    kind: ChangeKind = ChangeKind.RECURRING
    #: Signed: negative for a new cost, positive for extra income or a saving.
    amount_minor_units: int
    start_month: int = 1
    end_month: int | None = None
    label: str = ""


class RunScenarioInput(BaseModel):
    currency: str = "RON"
    opening_balance_minor_units: int
    monthly_income_minor_units: int
    monthly_expenses_minor_units: int
    horizon_months: int = Field(default=12, ge=1, le=120)
    changes: list[ScenarioChangeInput] = Field(default_factory=list)


class MonthView(BaseModel):
    month: int
    net_minor_units: int
    closing_balance_minor_units: int


class RunScenarioOutput(BaseModel):
    currency: str
    closing_balance_minor_units: int
    total_change_delta_minor_units: int
    first_negative_month: int | None = None
    months: list[MonthView]
    source: str = "ScenarioEngine"


def build(service: ScenarioService) -> ToolDefinition:
    async def handler(context: ToolContext, arguments: RunScenarioInput) -> RunScenarioOutput:
        currency = arguments.currency
        scenario = ScenarioInput(
            opening_balance=Money(arguments.opening_balance_minor_units, currency),
            monthly_income=Money(arguments.monthly_income_minor_units, currency),
            monthly_expenses=Money(arguments.monthly_expenses_minor_units, currency),
            horizon_months=arguments.horizon_months,
            changes=tuple(
                ScenarioChange(
                    change_id=change.change_id,
                    kind=change.kind,
                    amount=Money(change.amount_minor_units, currency),
                    start_month=change.start_month,
                    end_month=change.end_month,
                    label=change.label,
                )
                for change in arguments.changes
            ),
        )

        projection = await service.simulate(context.principal, scenario)
        return RunScenarioOutput(
            currency=projection.currency,
            closing_balance_minor_units=projection.closing_balance.minor_units,
            total_change_delta_minor_units=projection.total_change_delta.minor_units,
            first_negative_month=projection.first_negative_month,
            months=[
                MonthView(
                    month=month.month,
                    net_minor_units=month.net.minor_units,
                    closing_balance_minor_units=month.closing_balance.minor_units,
                )
                for month in projection.months
            ],
        )

    return ToolDefinition(
        name=TOOL_NAME,
        description="Project a what-if financial scenario deterministically over N months.",
        input_model=RunScenarioInput,
        output_model=RunScenarioOutput,
        handler=handler,
        allowed_agents=frozenset({"financial_advisor"}),
        required_permissions=frozenset({Permission.ACCOUNTS_READ}),
        side_effect=SideEffect.COMPUTE,
        risk_level=RiskLevel.LOW,
        tags=("cashplay", "deterministic"),
    )
