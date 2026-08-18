"""Deterministic money arithmetic.

Money is stored as an integer number of *minor units* (bani, cents) plus an
ISO-4217 currency code. Floating point is never used for balances or amounts.

Rules:

* operations between different currencies raise ``ValidationError``;
* rounding is explicit (banker's rounding by default);
* :meth:`Money.allocate` splits an amount without losing or inventing minor
  units, which is what split-payment settlement requires.

The AI layer may *explain* these values; it never computes them.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Sequence

from libra.core.errors import ValidationError

#: Minor units per major unit for the currencies Libra Galaxy handles today.
#: Currencies with a different exponent (e.g. JPY) must be added explicitly.
_MINOR_UNITS = {"RON": 100, "EUR": 100, "USD": 100}

DEFAULT_CURRENCY = "RON"


@dataclass(frozen=True, order=False)
class Money:
    """An exact monetary amount."""

    minor_units: int
    currency: str = DEFAULT_CURRENCY

    def __post_init__(self) -> None:
        if not isinstance(self.minor_units, int) or isinstance(self.minor_units, bool):
            raise ValidationError("Money.minor_units must be an integer.")
        if self.currency not in _MINOR_UNITS:
            raise ValidationError(f"Unsupported currency: {self.currency!r}")

    # -- construction -----------------------------------------------------
    @classmethod
    def zero(cls, currency: str = DEFAULT_CURRENCY) -> Money:
        return cls(0, currency)

    @classmethod
    def from_major(cls, amount: Decimal | int | str, currency: str = DEFAULT_CURRENCY) -> Money:
        """Build from a major-unit amount (e.g. ``"12.34"`` RON)."""
        if currency not in _MINOR_UNITS:
            raise ValidationError(f"Unsupported currency: {currency!r}")
        scale = _MINOR_UNITS[currency]
        value = (Decimal(str(amount)) * scale).quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
        return cls(int(value), currency)

    # -- conversion -------------------------------------------------------
    @property
    def major_amount(self) -> Decimal:
        """Exact decimal representation, safe for formatting and reporting."""
        return Decimal(self.minor_units) / Decimal(_MINOR_UNITS[self.currency])

    def to_dict(self) -> dict[str, object]:
        """Wire representation: exact integer plus a display-ready decimal.

        ``amount`` always carries the currency's full exponent ("2500.00", not
        "2500"), so clients never have to guess how many decimals to render.
        """
        exponent = len(str(_MINOR_UNITS[self.currency])) - 1
        return {
            "minor_units": self.minor_units,
            "currency": self.currency,
            "amount": f"{self.major_amount:.{exponent}f}",
        }

    # -- arithmetic -------------------------------------------------------
    def _check(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValidationError(
                f"Cannot combine {self.currency} with {other.currency}."
            )

    def __add__(self, other: Money) -> Money:
        self._check(other)
        return Money(self.minor_units + other.minor_units, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check(other)
        return Money(self.minor_units - other.minor_units, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.minor_units, self.currency)

    def __lt__(self, other: Money) -> bool:
        self._check(other)
        return self.minor_units < other.minor_units

    def __le__(self, other: Money) -> bool:
        self._check(other)
        return self.minor_units <= other.minor_units

    def scale(self, factor: Decimal | int | str, rounding: str = ROUND_HALF_EVEN) -> Money:
        """Multiply by a ratio (percentages, allocation rules, indexation)."""
        value = (Decimal(self.minor_units) * Decimal(str(factor))).quantize(
            Decimal(1), rounding=rounding
        )
        return Money(int(value), self.currency)

    def times(self, count: int) -> Money:
        """Repeat an amount a whole number of times (monthly projections)."""
        if not isinstance(count, int) or isinstance(count, bool):
            raise ValidationError("Money.times expects an integer count.")
        return Money(self.minor_units * count, self.currency)

    def allocate(self, weights: Sequence[int]) -> list[Money]:
        """Split across integer weights without losing minor units.

        The remainder is distributed one minor unit at a time in weight order,
        so ``sum(result) == self`` always holds. This is the deterministic base
        for split payments and settlement plans.
        """
        if not weights or any(w < 0 for w in weights) or sum(weights) <= 0:
            raise ValidationError("allocate() requires positive integer weights.")

        total_weight = sum(weights)
        shares = [self.minor_units * w // total_weight for w in weights]
        remainder = self.minor_units - sum(shares)
        step = 1 if remainder >= 0 else -1

        index = 0
        while remainder != 0:
            shares[index % len(shares)] += step
            remainder -= step
            index += 1

        return [Money(share, self.currency) for share in shares]


def sum_money(amounts: Sequence[Money], currency: str = DEFAULT_CURRENCY) -> Money:
    """Sum a sequence, returning ``Money.zero(currency)`` when empty."""
    total = Money.zero(currency)
    for amount in amounts:
        total = total + amount
    return total
