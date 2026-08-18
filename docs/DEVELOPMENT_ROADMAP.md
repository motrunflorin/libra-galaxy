# Development Roadmap

Eight phases, ordered by dependency rather than by excitement. Each phase ends
with something testable and demonstrable.

---

## Phase 0 — Foundation ✅ complete

Architecture designed, documented and materialised.

Delivered: monorepo layout; FastAPI application with the response envelope,
error hierarchy, request correlation and structured logging; typed
configuration with deployment-safety validation; `Money`; security primitives
(principal, roles, permissions, guards); repository contracts with in-memory
and MongoDB implementations; index declarations; the AI platform skeleton
(provider interfaces, tool contract/registry/eligibility/executor, agent
contract and the five specifications, context builder, conversation and memory
models, RAG chunking/indexing/retrieval, telemetry, orchestrator); the CashPlay
scenario engine; the Next.js shell with RO/EN localization and the typed API
client; Docker development stack; **135 tests**, including executable
architecture rules.

---

## Phase 1 — Banking core

**Goal:** a signed-in user sees their real accounts and transactions.

* Authentication: registration, login, Argon2id hashing, access/refresh tokens,
  rotation and revocation; replace the development principal resolver.
* Rate limiting on authentication endpoints.
* MongoDB repositories for identity, accounts and transactions; seed script.
* Transaction listing with filters and pagination; deterministic spending
  summaries.
* Frontend: login, dashboard, accounts and transactions, RO/EN throughout.
* Tests: authentication, token lifecycle, cross-user isolation on every new
  endpoint.

**Exit:** two users cannot see each other's data, proven by tests, on Mongo.

---

## Phase 2 — Agent platform

**Goal:** the pipeline runs end to end against Microsoft Foundry.

* `MicrosoftFoundryChatProvider` wired and exercised against a real deployment.
* Prompt assembly from `AssembledContext`, with prompt versioning.
* Conversation persistence, recent window, incremental compression.
* Tools: `get_transactions`, `get_spending_summary`, `get_savings_goals`.
* Telemetry to Mongo: `agent_runs`, `tool_invocations`, `ai_usage_records`.
* Tests: prompt assembly, budget enforcement, telemetry completeness, clean
  failure when Foundry is unavailable.

**Exit:** a turn reaches the model, executes tools, returns an answer and is
fully recorded — with no agent-specific logic yet.

---

## Phase 3 — First production agent: Transaction Intelligence

Chosen because its outputs are discrete and measurable against ground truth,
so the team learns to *evaluate* agents rather than judge them by impression.

* Deterministic first: merchant normalisation rules, category rules, recurring
  payment detection. The model handles only what the rules could not.
* Agent implementation, prompt `transactions-v1`, structured outputs.
* Evaluation harness + labelled dataset; accuracy, precision/recall and
  false-positive metrics in CI.
* Frontend: categorised transactions, detected subscriptions, user review.

**Exit:** measurable accuracy on a fixed dataset, tracked per prompt version.

---

## Phase 4 — RAG and memory

* Document ingestion; Mongo-backed vector index (Atlas Vector Search) behind
  the existing `VectorIndex` interface.
* Embedding cache and incremental re-indexing in production; `libra reindex`.
* Retrieval profiles per corpus; RO/EN filters; citation rendering.
* Durable user memory with expiry; cross-session recall, per user.
* Document Intelligence agent with citation-coverage evaluation.
* Frontend: document upload, document Q&A with visible sources.

**Exit:** cited answers over the real corpus, with retrieval quality measured
separately for RO and EN.

---

## Phase 5 — Advanced financial intelligence

* Payments: prepare/confirm/execute with idempotency and audit.
* Split payments, groups and settlement (`Money.allocate`).
* Savings goals and the allocation rules engine.
* Financial health: deterministic indicators and score components, with
  snapshots so a change is explainable.
* CashPlay UI over the existing scenario engine.
* Financial Advisor agent with numeric-fidelity evaluation.

**Exit:** money moves safely — confirmed, idempotent, audited — and the
assistant explains figures it never computed.

---

## Phase 6 — KYC, documents, proactive

* Document ingestion pipeline and an OCR service abstraction (no generic
  vision infrastructure).
* KYC workflow states with a mandatory human-review boundary.
* Compliance/KYC agent (assistive only).
* Notifications and preferences; Engagement agent for phrasing.
* Admin area: user administration and the AI observability dashboard.
* GDPR erasure workflow.

---

## Phase 7 — Voice, gamification, polish

* `VoiceProvider` implementation; transcript → same orchestrator.
* Achievements and savings streaks.
* Accessibility audit, performance budget, visual design pass.

---

## Five-person parallel plan

Ownership is by **stream**, not by feature, so nobody is permanently coupled to
one agent and no stream blocks another for long. Interfaces are agreed first;
the composition root is the only place streams meet.

| Stream | Owns | Phase 1–2 work |
| --- | --- | --- |
| **A — Platform & Security** | `core/*`: config, errors, security, envelope, logging, container, CI, Docker | Authentication, tokens, rate limiting, CI pipeline, index application |
| **B — Banking Domains** | `domains/*`: accounts, transactions, payments, savings | Mongo repositories, transaction filters, spending summaries, seed data |
| **C — Data & Persistence** | Mongo schema, indexes, migrations, seeds, performance | Index tuning, seed generator, query performance, Atlas Vector Search setup |
| **D — AI Platform** | `ai/*`: orchestrator, tools, context, memory, telemetry | Foundry provider, prompt assembly, conversation persistence, telemetry sinks |
| **E — Frontend** | `apps/web/*`: features, components, i18n, accessibility | Login, dashboard, accounts, transactions, RO/EN, error handling |

**Agents are shared work.** When an agent is implemented, one owner drives it
and pairs with the domain stream that supplies its tools — D owns the agent
runtime, B owns the services it reads, and the agent's evaluation dataset is
written by whoever knows the domain best.

### What can run in parallel from day one

```text
A: authentication            ──┐
B: Mongo repositories        ──┤ meet at the container + repository interfaces
C: indexes and seed data     ──┘

D: Foundry provider + prompts ── depends only on tool interfaces (already fixed)
E: frontend features          ── depends only on the API contract (already fixed)
```

E is unblocked because the envelope, error codes and `Money` shape are already
fixed and typed in `apps/web/src/lib/api/types.ts`. D is unblocked because the
tool contract is already fixed — new tools can be written against services that
B is still implementing, using the in-memory repositories.

### Conflict-avoidance rules

1. One stream owns a directory; changes elsewhere go through a short review by
   that owner.
2. Interfaces change by agreement first, implementation second.
3. `core/container.py` is the only shared file that everyone edits — keep those
   edits small and additive.
4. New tools land with schemas, permissions, side effect and risk level in the
   same commit. Never "wire it up now, secure it later".
5. Every PR keeps `pytest` green, including the architecture-boundary tests.
   Those tests exist so five people can move fast without eroding the design.

---

## Definition of done for a feature

* Service tests, including an authorization test.
* API contract test asserting the envelope and error codes.
* Cross-user isolation test if the feature touches user data.
* Deterministic calculation covered by exact-value tests.
* Structured logging on the new path, with no sensitive payloads.
* RO and EN strings present for anything user-visible.
* Documentation updated when a boundary or contract changed.
