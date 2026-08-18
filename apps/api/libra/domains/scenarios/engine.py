"""Deterministic scenario engine.

Given the current financial state and a set of changes, project the balance
month by month using exact integer arithmetic. Same input, same output, no
model involved.

The Financial Advisor agent may only *explain* a :class:`ScenarioProjection`;
it never produces the numbers.
"""

from __future__ import annotations

from libra.core.errors import ValidationError
from libra.core.money import Money, sum_money
from libra.domains.scenarios.models import (
    ChangeKind,
    MonthProjection,
    ScenarioChange,
    ScenarioInput,
    ScenarioProjection,
)

MAX_HORIZON_MONTHS = 120


class ScenarioEngine:
    """Pure projection. No repositories, no I/O, no randomness."""

    def project(self, scenario: ScenarioInput) -> ScenarioProjection:
        self._validate(scenario)

        currency = scenario.opening_balance.currency
        balance = scenario.opening_balance
        months: list[MonthProjection] = []
        first_negative: int | None = None

        for month in range(1, scenario.horizon_months + 1):
            delta = sum_money(
                [
                    change.amount
                    for change in scenario.changes
                    if self._applies(change, month)
                ],
                currency,
            )
            net = scenario.monthly_income - scenario.monthly_expenses + delta
            balance = balance + net

            if first_negative is None and balance.minor_units < 0:
                first_negative = month

            months.append(
                MonthProjection(
                    month=month,
                    income=scenario.monthly_income,
                    expenses=scenario.monthly_expenses,
                    change_delta=delta,
                    net=net,
                    closing_balance=balance,
                )
            )

        return ScenarioProjection(
            currency=currency,
            opening_balance=scenario.opening_balance,
            closing_balance=balance,
            total_change_delta=sum_money([item.change_delta for item in months], currency),
            first_negative_month=first_negative,
            months=tuple(months),
        )

    @staticmethod
    def _applies(change: ScenarioChange, month: int) -> bool:
        if month < change.start_month:
            return False
        if change.kind is ChangeKind.ONE_OFF:
            return month == change.start_month
        return change.end_month is None or month <= change.end_month

    @staticmethod
    def _validate(scenario: ScenarioInput) -> None:
        if not 1 <= scenario.horizon_months <= MAX_HORIZON_MONTHS:
            raise ValidationError(
                f"The horizon must be between 1 and {MAX_HORIZON_MONTHS} months."
            )

        currency = scenario.opening_balance.currency
        amounts: list[Money] = [scenario.monthly_income, scenario.monthly_expenses]
        amounts.extend(change.amount for change in scenario.changes)
        for amount in amounts:
            if amount.currency != currency:
                raise ValidationError("All scenario amounts must share one currency.")

        if scenario.monthly_income.minor_units < 0 or scenario.monthly_expenses.minor_units < 0:
            raise ValidationError("Monthly income and expenses cannot be negative.")

        for change in scenario.changes:
            if change.start_month < 1:
                raise ValidationError("A change cannot start before month 1.")
            if change.end_month is not None and change.end_month < change.start_month:
                raise ValidationError("A change cannot end before it starts.")
