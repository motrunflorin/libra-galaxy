# ADR 0001 — Modular monolith with executable boundaries

**Status:** Accepted · Phase 0

## Context

Five developers, one product, no traffic yet. Microservices were considered
because the domain decomposes cleanly (accounts, payments, AI). The real risk
at this stage is not scaling — it is boundary erosion: a router querying
MongoDB directly, an agent importing a repository, banking logic drifting into
the frontend.

## Decision

A modular monolith: one FastAPI deployable with four layers (`core`,
`domains`, `ai`, `api`) and a strict downward dependency rule. The rules are
enforced by `tests/test_architecture_boundaries.py`, which parses every
module's imports and fails the build on a violation.

## Consequences

**Good.** One deployment, one test run, no distributed debugging. Boundaries
are checked mechanically rather than in review, which is what lets five people
move in parallel. Any module can be extracted later because nothing crosses a
boundary today.

**Cost.** Everything scales together, and the whole application restarts on
deploy. Acceptable at this stage.

**Extraction signal.** Extract a module when it needs independent scaling, an
independent release cadence, or a different runtime — not because the
directory got large.
