# ADR 0005 — Money as integer minor units

**Status:** Accepted · Phase 0

## Context

Amounts must be exact. Floats are unusable for money;
`Decimal` is correct but easy to misuse (mixed currencies, implicit rounding,
serialisation drift through JSON).

## Decision

`Money(minor_units: int, currency: str)`. Construction from a major-unit
decimal, exact decimal output for display, explicit rounding (banker's by
default), and mixed-currency operations raising `ValidationError`.

`Money.allocate(weights)` splits an amount across integer weights and
distributes the remainder one minor unit at a time, so `sum(parts) == total`
always holds.

On the wire: `{"minor_units": 250000, "currency": "RON", "amount": "2500.00"}`.
`minor_units` is the value; `amount` is for display only.

## Consequences

**Good.** No rounding drift. `allocate` gives split-payment settlement an exact
foundation on day one. Currency mistakes fail loudly at the boundary. JSON
carries an integer, so no precision is lost in transport.

**Cost.** Every amount must be constructed deliberately, and currencies with a
different exponent must be added to `_MINOR_UNITS` explicitly rather than
assumed.
