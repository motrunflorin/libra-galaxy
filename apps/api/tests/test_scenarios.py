"""CashPlay: the projection must be deterministic and read-only."""

from __future__ import annotations

import pytest

from libra.core.errors import ValidationError
from libra.core.money import Money
from libra.domains.scenarios.engine import ScenarioEngine
from libra.domains.scenarios.models import ChangeKind, ScenarioChange, ScenarioInput
from tests.conftest import run


def _scenario(**kwargs) -> ScenarioInput:
    defaults = dict(
        opening_balance=Money(100_000, "RON"),
        monthly_income=Money(500_000, "RON"),
        monthly_expenses=Money(400_000, "RON"),
        horizon_months=12,
    )
    defaults.update(kwargs)
    return ScenarioInput(**defaults)


def test_baseline_projection_is_exact() -> None:
    projection = ScenarioEngine().project(_scenario())
    # opening + 12 * (income - expenses)
    assert projection.closing_balance == Money(100_000 + 12 * 100_000, "RON")
    assert projection.horizon_months == 12


def test_projection_is_reproducible() -> None:
    engine = ScenarioEngine()
    first = engine.project(_scenario())
    second = engine.project(_scenario())
    assert first == second


def test_recurring_subscription_reduces_every_month_from_its_start() -> None:
    projection = ScenarioEngine().project(
        _scenario(
            changes=(
                ScenarioChange(
                    change_id="gym",
                    kind=ChangeKind.RECURRING,
                    amount=Money(-20_000, "RON"),
                    start_month=3,
                    label="Gym membership",
                ),
            )
        )
    )

    assert projection.months[1].change_delta == Money(0, "RON")
    assert projection.months[2].change_delta == Money(-20_000, "RON")
    assert projection.total_change_delta == Money(-20_000 * 10, "RON")


def test_one_off_purchase_applies_once() -> None:
    projection = ScenarioEngine().project(
        _scenario(
            changes=(
                ScenarioChange(
                    change_id="laptop",
                    kind=ChangeKind.ONE_OFF,
                    amount=Money(-500_000, "RON"),
                    start_month=2,
                ),
            )
        )
    )

    assert projection.total_change_delta == Money(-500_000, "RON")
    assert projection.months[1].change_delta == Money(-500_000, "RON")
    assert projection.months[2].change_delta == Money(0, "RON")


def test_cancelled_subscription_is_a_positive_change() -> None:
    projection = ScenarioEngine().project(
        _scenario(
            changes=(
                ScenarioChange(
                    change_id="netflix-cancelled",
                    kind=ChangeKind.RECURRING,
                    amount=Money(5_000, "RON"),
                    end_month=6,
                ),
            )
        )
    )
    assert projection.total_change_delta == Money(30_000, "RON")


def test_first_negative_month_is_reported() -> None:
    projection = ScenarioEngine().project(
        _scenario(
            monthly_income=Money(100_000, "RON"),
            monthly_expenses=Money(150_000, "RON"),
            horizon_months=6,
        )
    )
    # 100_000 opening, -50_000 per month: negative from month 3.
    assert projection.first_negative_month == 3


def test_mixed_currencies_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ScenarioEngine().project(_scenario(monthly_income=Money(1, "EUR")))


def test_horizon_is_bounded() -> None:
    with pytest.raises(ValidationError):
        ScenarioEngine().project(_scenario(horizon_months=999))


def test_simulation_does_not_touch_account_state(container, alice, accounts_repository) -> None:
    before = run(container.accounts.list_accounts(alice))[0].balance

    run(container.scenarios.simulate(alice, _scenario()))

    after = run(container.accounts.list_accounts(alice))[0].balance
    assert before == after
