"""Money arithmetic must be exact: this is the base of every banking figure."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libra.core.errors import ValidationError
from libra.core.money import Money, sum_money


def test_from_major_converts_without_float_error() -> None:
    assert Money.from_major("12.34").minor_units == 1234
    assert Money.from_major(Decimal("0.1")) + Money.from_major(Decimal("0.2")) == Money.from_major(
        Decimal("0.3")
    )


def test_currency_mismatch_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Money(100, "RON") + Money(100, "EUR")


def test_scale_uses_bankers_rounding() -> None:
    # 0.5 minor units round to even, so results stay unbiased over many rows.
    assert Money(101, "RON").scale(Decimal("0.5")).minor_units == 50
    assert Money(103, "RON").scale(Decimal("0.5")).minor_units == 52


def test_allocate_never_loses_or_invents_minor_units() -> None:
    parts = Money(10_000, "RON").allocate([1, 1, 1])
    assert [part.minor_units for part in parts] == [3334, 3333, 3333]
    assert sum_money(parts, "RON") == Money(10_000, "RON")


def test_allocate_handles_negative_totals() -> None:
    parts = Money(-10_001, "RON").allocate([1, 1])
    assert sum_money(parts, "RON") == Money(-10_001, "RON")


def test_allocate_respects_weights() -> None:
    parts = Money(1_000, "RON").allocate([3, 1])
    assert [part.minor_units for part in parts] == [750, 250]


def test_wire_representation_keeps_exact_integer() -> None:
    assert Money(1234, "RON").to_dict() == {
        "minor_units": 1234,
        "currency": "RON",
        "amount": "12.34",
    }


def test_wire_amount_always_carries_the_currency_exponent() -> None:
    # A whole amount must still render as "2500.00", so clients never guess.
    assert Money(250_000, "RON").to_dict()["amount"] == "2500.00"
    assert Money(0, "EUR").to_dict()["amount"] == "0.00"
    assert Money(-5, "USD").to_dict()["amount"] == "-0.05"
