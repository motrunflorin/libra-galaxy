# Technical Interviewer — Pattern Adoption

What Libra Galaxy took from the reference project at
`/home/regelepirat/AI-Academy/technical-interviewer-chatbot`, what it changed,
and what it left behind.

The reference repository is **read-only engineering material**. Nothing in it
was modified. No code was copied verbatim; every adopted idea was reimplemented
for banking constraints.

Read alongside [`ENGINEERING_FEEDBACK.md`](ENGINEERING_FEEDBACK.md), which
scopes fallback and vision infrastructure out.

---

## 1. Adopted and improved

### Registry-driven knowledge catalogue

*Reference:* `knowledge/*/registry.json` declares which Markdown documents
exist and which are always loaded; `KnowledgeLoader` refuses to load anything
undeclared.

*Why it works:* the corpus is governed, not discovered. A file dropped in a
directory does not silently become part of the model's context.

*Libra Galaxy:* kept, extended with the metadata a bank needs to answer "which
version of which document produced this answer?" — `document_type`,
`language`, `version`, `audience`, `checksum`, and `owner_user_id` for user
documents. `audience` and `owner_user_id` are retrieval **filters**, so
staff-only content and other users' documents cannot be retrieved at all.

### Content-addressed chunk ids + incremental re-indexing

*Reference:* `_chunk_id = sha256(category, document_id, position, text)`;
re-index embeds only ids that are missing and deletes ids no longer desired.

*Why it works:* an unchanged paragraph keeps its id and its embedding. Editing
one section does not re-embed a corpus.

*Libra Galaxy:* kept, with the planning logic extracted into a **pure
function** (`plan_reindex`) so re-indexing behaviour is unit-testable without a
database or a provider — five tests cover reuse, partial change, deletion and
embedding-space switching.

*Limitation fixed:* the reference computed a plan against "whatever provider
answered", and its `search_service` could mutate the active provider mid-query
and reload the whole chunk list. Libra Galaxy makes the embedding space
explicit — `provider:deployment:embedding_version` — and every plan, vector and
comparison is scoped to one key. Changing a deployment rebuilds cleanly instead
of silently mixing vector spaces.

### Embedding cache and query-embedding cache

*Reference:* SQLite tables keyed by `(provider, model, chunk_id)` and
`sha256(provider, model, query)`.

*Libra Galaxy:* kept, keyed by `embedding_key` + content hash, with a 30-day
TTL index (a cache is not an archive). Queries are hashed, so a customer's
question is never stored in plaintext.

### Tool registry with auditable selection reasons

*Reference:* `Tool(name, description, callback)` in a registry;
`SelectedTool(name, reason)` records *why* a tool ran; the executor returns
structured per-tool results.

*Why it works:* "why did the assistant do that?" is answerable from data.

*Libra Galaxy:* kept the reason, and added everything a bank must declare:
input/output **schemas** (validated in both directions), `allowed_agents`,
`required_permissions`, `side_effect`, `risk_level`, `requires_confirmation`.

*Limitation fixed:* the reference's tools were unrestricted — any tool could
run for any request, because there were no users and no permissions. Here,
eligibility is a separate, tested module evaluated before execution and
re-checked at execution.

### Parallel tool execution with timeouts

*Reference:* `asyncio.gather` over selected tools, each with a timeout, sync
callbacks offloaded to a thread; failures returned as results rather than
raised.

*Libra Galaxy:* kept, with a **barrier**: only `read_only`/`compute` tools run
concurrently; anything that prepares or performs a mutation runs alone, after
queued reads complete. Financial mutations are never speculative.

### Deterministic, explainable tool selection

*Reference:* a rule-based selector with RO/EN keyword tables and an explicit
reason per match — no model call to decide which tool to use.

*Why it works:* free, instant, reproducible, testable.

*Libra Galaxy:* the same instinct, applied to **intent classification** and
**agent routing**. Phrase tables moved out of the orchestrator into
`ai/orchestration/intent.py` as data, with diacritic-insensitive matching (so
"cheltuit" and "cheltuiț" both match) and priority ordering (so "transfer" is
not swallowed by a broader match). Ten parametrised tests cover RO and EN.

### Layered context assembly with per-section budgets

*Reference:* `assemble_system_prompt()` joins labelled sections — base prompt,
session summary, cross-session memory, procedures, retrieved knowledge, tool
evidence — each capped by its own character budget.

*Why it works:* a long conversation cannot crowd out the evidence.

*Libra Galaxy:* generalised into a `ContextBuilder` with typed
`ContextSection`s carrying `source` and `provenance`, per-source budgets, fixed
ordering, and recorded truncation. Crucially, `ContextSource.is_authoritative`
is what separates banking figures from recollection — the distinction the
reference had no need for.

### Conversation compression

*Reference:* `compact()` folds messages older than the recent window into a
`summary` column, leaving visible history untouched.

*Libra Galaxy:* kept the idea, fixed the cost: the reference re-read the entire
message list on every turn and rewrote the summary from scratch. Here a
`summary_watermark` makes compression incremental, so cost per turn is constant
regardless of conversation length. Compression remains deterministic (no model
call), which keeps it free and reproducible; swapping in an LLM summariser is a
one-method change.

### Structured JSONL logging with an event payload

*Reference:* a JSON formatter merging `record.event_data` into each line.

*Libra Galaxy:* kept, plus automatic correlation ids from context variables
(`request_id`, `user_id`) and a **redaction filter** applied before writing.

### Per-turn metrics: tokens, cost, latency, trace

*Reference:* `TurnMetric` with usage, latency, model rationale, trace, tool
results and retrieval hits, persisted and rendered on a live dashboard.

*Why it works:* it makes AI behaviour and spend visible from day one.

*Libra Galaxy:* kept the shape, **removed the content**. The reference stored
the full question and answer in its metrics table; in a bank those strings are
customer financial data. `AgentRunRecord` holds identifiers, counts, durations,
token usage, cost and stage names — enough to debug and to bill, not enough to
leak.

### Token counting with a graceful fallback

*Reference:* `tiktoken` when importable, `len(text)/4` otherwise.

*Libra Galaxy:* kept as-is — cost tracking still works in environments without
the optional dependency.

### Capability-based model separation

*Reference:* one deployment for chat, another for embeddings, chosen by task.

*Libra Galaxy:* kept. Deployment names are configuration; no sophisticated
model router, per `ENGINEERING_FEEDBACK.md`.

---

## 2. Adopted structurally, rebuilt in implementation

### Provider abstraction

The reference's `LLMRouter` mixed two jobs: abstracting a provider and
*failing over* to a local one. Libra Galaxy keeps the abstraction
(`ChatProvider`, `EmbeddingProvider`, `VoiceProvider`) and removes the failover
entirely. One implementation each; unavailability raises
`AI_PROVIDER_UNAVAILABLE`.

### Session management

The reference identified conversations by a client-supplied `session_id` with
no owner — correct for a single-user demo, unusable in a bank. Here a
conversation is a **user-owned resource**: every repository method takes
`user_id`, and a foreign conversation returns not-found.

### Cross-session memory

The reference pulled summaries from *other sessions* into the current prompt.
In a multi-user system that is a data leak. Libra Galaxy scopes memory to one
user, types it (`PREFERENCE`, `STATED_INTENT`, `CONVERSATIONAL_FACT`), gives it
an expiry, and states explicitly that it is never banking state.

### Vector search

The reference loaded every vector into a Python list and scanned it per query —
fine for a few hundred chunks, wrong for a growing corpus. Libra Galaxy defines
a `VectorIndex` interface (Atlas Vector Search in production, brute force in
tests) so the storage decision stays reversible.

---

## 3. Deliberately not adopted

| Pattern | Why not |
| --- | --- |
| Azure → Ollama chat/embedding fallback | Explicit non-goal. A cheaper answer that is wrong about a balance is not a saving. Guarded by a test |
| Local model infrastructure | Out of scope |
| Vision service (`qwen2.5vl`), vision context injection | Explicit non-goal. KYC will use a dedicated OCR abstraction, not generic vision |
| Import-time singletons (`chat_service = ChatService()`, `metrics_store`, `tool_executor`) | Hidden global state; untestable; no per-environment configuration. Replaced by a composition root, enforced by a test |
| Module-level constants as configuration, with the endpoint hard-coded in source | Replaced by validated, environment-driven settings; only `core.config` reads the environment |
| Mutable shared index state (a query mutating `active_provider` and reloading chunks) | A read request must not mutate global state |
| SQLite runtime store | MongoDB, behind repository interfaces |
| Bare dicts from routers, `HTTPException(500, detail=str(error))` | Leaks internals. Replaced by the envelope plus an error hierarchy with stable codes |
| `<answer>`/`<rationale>` tag parsing | Structured agent responses with typed fields instead of tag scraping |
| Interview domain: CV analysis, question generation, candidate feedback, study plans, interview prompts/procedures | Different product. Guarded by `test_no_interview_domain_leaked_from_the_reference_project` |
| CLI-oriented features (console turn printer, DOCX/PDF conversation reports) | Not useful for a web banking product; document generation will be a banking-specific feature |
| An empty `tests/` directory behind a `main.py test` command | Libra Galaxy ships 135 tests in Phase 0 |

---

## 4. Net additions with no reference counterpart

Authentication and multi-user isolation; roles and permissions; ownership
guards; tool permissions and risk levels; confirmation requirements; risk
classification; explicit multi-step workflow state; audit events; exact
integer money arithmetic; repository interfaces; the four-family separation of
state; executable architecture-boundary tests.

---

## 5. How to borrow the next pattern

1. Read the reference implementation.
2. Work out *why* it worked there.
3. Check `ENGINEERING_FEEDBACK.md` for scope constraints.
4. Identify the limitation a bank would hit — usually multi-user isolation,
   auditability, or treating model output as fact.
5. Redesign for that constraint.
6. Implement in Libra Galaxy, with tests.
7. Record the adaptation here.

Never copy the file across.
