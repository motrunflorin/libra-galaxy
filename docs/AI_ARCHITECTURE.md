# AI Architecture

The AI layer analyses, explains, retrieves, simulates and prepares. It does not
decide what is true about money.

---

## 1. Four sources, never mixed

| Source | Authoritative? | Example question |
| --- | --- | --- |
| Banking services | **Yes** | "What is my balance right now?" |
| Conversation memory | No | "What savings plan did we discuss yesterday?" |
| RAG knowledge | No (cited, not authoritative) | "How do allocation rules work?" |
| Model output | Never | — |

Every block of context is tagged with a `ContextSource`, and only
`BANKING_STATE` / `TOOL_RESULT` report `is_authoritative == True`. The rendered
prompt labels each block, so the model is told which figures are real and which
are recollection:

```text
## Your accounts
[source=banking_state id=banking_state:accounts]
...
```

---

## 2. The orchestration pipeline

```text
request
  → authentication      Principal resolved at the HTTP edge
  → authorization       assistant:use permission checked before any model work
  → intent              deterministic RO/EN rules (IntentClassifier)
  → risk                derived from intent, never from message wording
  → context             ContextBuilder, per-source budgets, provenance
  → agent selection     deterministic lookup (AgentRouter)
  → tool eligibility    agent ∩ permissions ∩ risk ceiling ∩ confirmation
  → execution           agent runs, tools execute through services
  → validation          agent stayed inside its declared tool contract
  → response            user-facing fields only
  → telemetry           AgentRunRecord + ToolInvocationRecord + UsageRecord
```

Every stage appends a `TraceEntry`. **The trace is internal.** It goes to logs
and the admin dashboard; a banking customer receives only `text`, `data` and
`citations`.

### Why deterministic routing

An intent lookup table is free, instant, reproducible and unit-testable. A
model call to decide "is this a spending question?" costs latency and money and
cannot be regression-tested cheaply. Model-based classification is reserved for
the `UNKNOWN` bucket — the only place where it adds value.

### Risk

Risk is computed from the *intent*, never from the message text, so no phrasing
can lower a ceiling. It produces:

* `level` — recorded in telemetry;
* `tool_ceiling` — the highest tool risk permitted for this request;
* `requires_confirmation` — `HIGH` intents (payments) never reach an agent
  unconfirmed; they raise `CONFIRMATION_REQUIRED` and the deterministic payment
  flow takes over.

The effective ceiling for a turn is `min(agent.risk_ceiling, risk.tool_ceiling)`.

---

## 3. Tools

A tool is the only bridge from an agent to application functionality. Every
tool declares, as data:

```python
ToolDefinition(
    name="get_accounts",
    input_model=GetAccountsInput,      # validated before the handler runs
    output_model=GetAccountsOutput,    # validated before it reaches the model
    allowed_agents={"financial_advisor", ...},
    required_permissions={Permission.ACCOUNTS_READ},
    side_effect=SideEffect.READ_ONLY,  # read_only | compute | prepares_mutation | mutates
    risk_level=RiskLevel.LOW,
    requires_confirmation=False,
)
```

Eligibility is decided by four independent conditions — agent allow-list,
permissions, risk ceiling, confirmation — and re-checked immediately before
execution, so a plan built earlier in the turn cannot smuggle a tool through.
A `MUTATES` tool that does not require confirmation fails at construction time.

### Parallelism

`READ_ONLY` and `COMPUTE` tools run concurrently. Anything that prepares or
performs a mutation acts as a **barrier**: queued reads finish, then it runs
alone. Financial mutations are never speculative.

```text
Financial Advisor
  ├── get_accounts        ┐
  ├── get_spending_summary├─ concurrent
  └── run_scenario        ┘
```

---

## 4. Multi-step workflows

Workflow state is an explicit, inspectable value (`WorkflowRun` /
`WorkflowStep` with `status`, `depends_on`, `duration_ms`, `output`), never a
model's hidden reasoning. A what-if question is a declared sequence:

```text
get_accounts (tool_call)
  → run_scenario (deterministic_calculation)
    → get_savings_goals (tool_call)
      → explain (agent_generation)
```

Each step can be inspected, retried and audited. The alternative — letting the
model decide the next step from its own scratchpad — is untestable and
unauditable, which is why it is not used.

---

## 5. Context building

One `ContextBuilder` assembles context for every agent; agents never gather
their own. Assembly is:

* **ordered** — fixed sequence, so prompts are reproducible;
* **budgeted per source** — a long conversation cannot displace balances;
* **honest about truncation** — shortened sections are recorded in
  `truncated_sections`, never silently dropped.

| Section | Budget (chars) | Priority |
| --- | --- | --- |
| identity / permissions / locale | 500 / 500 / 200 | always kept |
| conversation summary | 3 000 | medium |
| user memory | 2 000 | medium |
| recent conversation | 6 000 | medium |
| retrieved knowledge | 7 000 | medium |
| banking state | 6 000 | high |
| tool results | 5 000 | high |

---

## 6. Memory

Four separate things, deliberately not one:

1. **Recent turns** — verbatim, bounded window (12 messages).
2. **Conversation summary** — older turns, compressed incrementally against a
   `summary_watermark`, so cost per turn is constant regardless of history
   length.
3. **Durable user memory** — typed (`PREFERENCE`, `STATED_INTENT`,
   `CONVERSATIONAL_FACT`), scoped to one user, expiring.
4. **Banking state** — from services, every time, never remembered.

Compression is deterministic by default (one condensed line per folded turn):
reproducible, free, and it degrades safely. An LLM summariser can replace
`_compress_text` without touching the storage model.

Memory is **per user**. The reference project shared "cross-session memory"
across all sessions — correct for a single-user demo, a data leak in a bank.

---

## 7. RAG

```text
ingestion → normalization → metadata → chunking → embedding
   → indexing → retrieval → ranking → context injection → attribution
```

### Chunking

Strategy per document type, not one window for everything:

| Document type | Strategy | Why |
| --- | --- | --- |
| policy, procedure, product, FAQ | `section_aware` | A heading is a meaning boundary and a citable unit |
| financial education, user document, statement | `fixed_window` | No reliable structure to exploit |

Size and overlap are configuration (`LIBRA_RAG_CHUNK_*`). Chunk ids are
content-addressed (`sha256(document_id, position, text)`), which is what makes
incremental indexing work.

### Incremental re-indexing

`plan_reindex()` is a pure function comparing desired chunks against what is
indexed **for one embedding key**:

```text
unchanged chunk id → reuse existing vector
new/edited chunk   → embed
orphaned chunk id  → delete
```

The embedding key is `provider:deployment:embedding_version`. Changing the
deployment produces a clean rebuild under a new key instead of mixing
incompatible vectors — the failure mode the reference implementation had when
it swapped provider mid-run.

### Retrieval

Filters are applied **before** similarity, so an isolation rule can never be
outranked by a high cosine score:

* `languages` — RO/EN corpora retrieved separately;
* `document_types`;
* `audience` — staff-only content is never returned to a customer;
* `owner_user_id` — a user document is visible only to its owner; shared
  knowledge has no owner;
* `metadata_equals` — arbitrary governance filters.

Thresholds and `top_k` come from a named `RetrievalProfile`, not one global
constant, because one threshold is not right for both a FAQ and a statement.
Reranking is a defined seam between filtering and injection.

### What RAG must never answer

Balance, account ownership, exact transaction totals, payment state,
permissions, ledger state. Those go to services. This is stated in every agent
specification and is a review checklist item.

---

## 8. Providers

```text
ChatProvider       → MicrosoftFoundryChatProvider       (gpt-5-mini deployment)
EmbeddingProvider  → MicrosoftFoundryEmbeddingProvider  (text-embedding-3-small)
VoiceProvider      → (Microsoft, implementation TBD)
```

The interfaces exist for modularity and testability, **not for fallback**.
There is exactly one implementation of each. If Foundry is unavailable the
request fails with `AI_PROVIDER_UNAVAILABLE` — observable, honest, and never a
silent downgrade to a different model with different behaviour.

Deployment names come from configuration and appear in no business logic.

---

## 9. Voice

Voice is a channel, not an agent:

```text
audio → VoiceProvider.transcribe → same Orchestrator → same agents and tools
      → response text → VoiceProvider.synthesize → audio
```

`Channel.VOICE` is recorded on the message for analytics and tone selection.
The concrete Microsoft service is intentionally undecided, so the interface
stays small and replaceable.

---

## 10. Observability and cost

Recorded per turn:

| Field | Purpose |
| --- | --- |
| `request_id`, `run_id`, `user_id`, `conversation_id` | Correlation |
| `agent_id`, `prompt_version`, `deployment` | Which version produced this |
| `intent`, `risk_level` | Routing quality analysis |
| `latency_ms`, `tool_count`, `retrieved_chunks`, `context_chars` | Performance |
| `success`, `error_code`, `stages` | Failure analysis |
| tokens in/out/cached, `estimated_cost_usd` | Cost per feature/agent/deployment |

**Not recorded:** the question, the answer, retrieved text, tool payloads. The
reference project stored full question and answer text in its metrics table;
in a bank those strings are customer financial data.

Cost is estimated with `estimate_chat_cost()` from configured per-million rates
(`LIBRA_AI_*_PRICE_PER_MILLION`), attributed by feature, agent, deployment and
environment.

---

## 11. Cost controls that do not compromise correctness

Kept: embedding cache, query-embedding cache (hashed keys — a customer's
question is never stored in plaintext), context compression, per-source context
budgets, incremental indexing, deterministic computation instead of a model
call, retrieval limits.

Rejected: falling back to a cheaper model to save money. A cheaper answer that
is wrong about someone's balance is not a saving.
