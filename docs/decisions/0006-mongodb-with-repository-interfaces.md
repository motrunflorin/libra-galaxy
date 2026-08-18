# ADR 0006 — MongoDB behind repository interfaces

**Status:** Accepted · Phase 0

## Context

MongoDB is the specified initial database and fits conversations, documents and
vectors well. A real financial ledger may later need stronger transactional
guarantees than a document store provides.

## Decision

Services depend on repository **interfaces** (`AccountRepository`,
`TransactionRepository`, `ConversationRepository`, …). MongoDB implementations
live in `*_repository.py` modules and are the only code allowed to import a
Mongo driver — enforced by an architecture test. An in-memory implementation
backs tests and local development, selected by configuration.

Indexes are declared as data in one module and applied at startup.

## Consequences

**Good.** The whole test suite runs without a database (135 tests, no
containers). Swapping the ledger's storage later is a repository change, not an
application rewrite. Index declarations are reviewable and testable — the
owner-first rule that makes user isolation cheap is asserted by a test.

**Cost.** Two implementations to keep in step for each repository, and the
in-memory one can hide a query mistake that only Mongo would reveal. Mitigated
by keeping in-memory implementations trivially simple, and by integration tests
against real MongoDB from Phase 1.
