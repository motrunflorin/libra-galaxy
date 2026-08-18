# ADR 0002 — The AI layer is never authoritative about money

**Status:** Accepted · Phase 0

## Context

The product is an AI-native bank. The tempting shortcut is to let an agent read
the database and answer directly — fewer layers, faster to build. It is also
how an assistant ends up confidently stating a balance that is a month old, or
a summary sentence that becomes the number a customer acts on.

## Decision

Structural separation, not instructions in a prompt:

* `libra.domains` never imports `libra.ai`; banking correctness does not depend
  on the AI layer existing.
* Agents cannot import domains or database drivers; the only route is
  `Agent → Typed Tool → Application Service → Repository`.
* Tools declare permissions, side effects, risk and confirmation as data;
  eligibility is decided outside the model and re-checked at execution.
* Context sections carry a `source`, and only service-derived sections report
  `is_authoritative`.
* High-risk intents raise `CONFIRMATION_REQUIRED` before an agent runs.

## Consequences

**Good.** Deleting the entire AI layer leaves a correct bank. No prompt can
grant a capability. Every figure is traceable to the service that computed it.

**Cost.** Every new agent capability needs a typed tool first, which is slower
than letting an agent query freely. That friction is the point.
