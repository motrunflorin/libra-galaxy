# ADR 0004 — Deterministic intent classification and agent routing

**Status:** Accepted · Phase 0

## Context

Something must decide whether "cât am cheltuit luna trecută?" goes to
Transaction Intelligence or the Financial Advisor. The obvious AI-native answer
is to ask a model.

## Decision

Rules first. `IntentClassifier` matches RO/EN phrase tables (diacritic
insensitive, priority ordered) and `AgentRouter` maps intent to agent through a
lookup table. Both are data, both are unit-tested. Model-based classification
is reserved for the `UNKNOWN` bucket, where a table genuinely cannot help.

`UNKNOWN` routes to Document Intelligence — the agent that must cite a source
for everything it says, which is the safest default.

## Consequences

**Good.** Zero latency and zero cost for the common case. Routing is
reproducible and regression-testable (ten parametrised cases today). A routing
bug is a data fix, not a prompt experiment.

**Cost.** Phrase tables need maintenance as vocabulary grows, and unusual
phrasings land in `UNKNOWN`. Both are visible in telemetry: a rising `UNKNOWN`
rate is the signal to extend the tables — or, at that point, to add model-based
classification for that bucket only.
