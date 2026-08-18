# ADR 0007 — A development principal resolver in Phase 0

**Status:** Accepted · Phase 0 · Superseded by real authentication in Phase 1

## Context

Authorization is the backbone of a multi-user bank, and Phase 0 is architecture
and foundation — full authentication (hashing, tokens, rotation, revocation,
rate limiting) is Phase 1 work. Building the authorization boundary without any
authentication would leave it untested; building full authentication now would
overrun the phase.

## Decision

`get_principal` accepts `Authorization: Bearer dev:<user_id>:<role>` and builds
a `Principal` with that role's permissions. It is refused outside `local`/`test`:
`load_settings` raises `CONFIGURATION_ERROR` if development authentication is
enabled in a deployed environment, and any other token format returns
`AUTH_INVALID`.

## Consequences

**Good.** Ownership and permission enforcement are real and tested from day one
(cross-user isolation, permission denial, staff limits). The frontend can be
developed against a working authenticated API. Phase 1 replaces one function —
everything downstream already depends on `Principal`.

**Risk.** A misconfigured deployment could in principle expose it. Mitigated by
startup validation, by the default being off in deployed environments, and by
`test_dev_auth_cannot_be_forced_on_in_production`.

**Removal criteria.** Deleted the moment Phase 1 authentication merges. It is
not a fallback and must not survive as one.
