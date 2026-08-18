# ADR 0003 — No automatic AI provider fallback

**Status:** Accepted · Phase 0

## Context

The reference project failed over from Azure to a local Ollama model when Azure
was unavailable, and this looked like good resilience engineering.

## Decision

Provider interfaces exist for modularity and testability. Exactly one
implementation of each (Microsoft Foundry). If Foundry is unavailable, the
request fails with `AI_PROVIDER_UNAVAILABLE`. No automatic switch.

An architecture test (`test_no_provider_fallback_infrastructure_exists`)
prevents the pattern from reappearing.

## Consequences

**Good.** Behaviour is predictable: one model, one set of safety properties,
one evaluation baseline. An outage is visible in monitoring instead of being
masked by a silently degraded answer. Evaluations remain meaningful, because
they measure the model that actually serves traffic.

**Cost.** AI features are unavailable during a Foundry outage. For a banking
assistant that explains money, "temporarily unavailable" is a better answer
than one produced by an unevaluated model.

**Revisit if** a second provider is evaluated to the same standard *and* the
routing decision is explicit and recorded — not automatic.
