# Database

MongoDB, accessed only through repository interfaces. Index declarations live
in `apps/api/libra/core/persistence/indexes.py` and are applied by
`libra indexes` and at application startup.

---

## 1. Four state families

They are kept apart because they differ in truth guarantee, retention and
access control. Mixing them is how a conversation summary ends up being treated
as a balance.

| Family | Truth | Retention | Who reads it |
| --- | --- | --- | --- |
| Authoritative banking | Source of truth | Regulatory (years) | Services only |
| AI / conversation | Recollection | User-controlled, expiring | Assistant, owner |
| Documents / RAG | Cited reference | Versioned | Retrieval, owner |
| Audit / observability | Immutable record | Policy-driven | Admin, compliance |

---

## 2. Collections

### Authoritative banking state

| Collection | Owner key | Notes |
| --- | --- | --- |
| `users` | `_id` | Credentials are stored hashed, never alongside profile data |
| `accounts` | `user_id` | `balance_minor_units` as integer + `currency`; never floats |
| `subaccounts` | `user_id` | Purpose-oriented spaces inside an account |
| `transactions` | `user_id` | `merchant_raw` kept verbatim, `merchant_key` normalized |
| `payments` | `user_id` | `idempotency_key` unique; states: prepared → confirmed → executed/failed |
| `payment_groups` | `member_user_ids` | Multi-owner: membership is the access rule |
| `group_expenses` | `group_id` | Shares computed with `Money.allocate` |
| `savings_goals` | `user_id` | Target amount, target date, progress |
| `allocation_rules` | `user_id` | Trigger + destinations; executed by a deterministic engine |
| `subscriptions` | `user_id` | Detected → user-reviewed → confirmed/dismissed |
| `financial_health_snapshots` | `user_id` | Component values kept, so a score change is explainable |

### AI and conversation state

| Collection | Owner key | Notes |
| --- | --- | --- |
| `ai_conversations` | `user_id` | Carries `summary_watermark` for incremental compression |
| `ai_messages` | `user_id` | `(conversation_id, sequence)`; `channel` is text or voice |
| `ai_conversation_summaries` | `user_id` | One per conversation; `covers_up_to_sequence` |
| `ai_user_memories` | `user_id` | Typed and expiring; **never** cross-user |

### Documents and RAG

| Collection | Owner key | Notes |
| --- | --- | --- |
| `documents` | `user_id` | Uploads, statements, exports |
| `document_chunks` | `user_id` | User-owned chunks; retrieval filters on owner |
| `knowledge_documents` | — (shared) | `(document_id, version)` unique; governance metadata |
| `knowledge_chunks` | — (shared) | `(embedding_key, chunk_id)` unique; `audience` filter |
| `embedding_cache` | — (shared) | Hashed keys only; 30-day TTL |

`embedding_key` is `provider:deployment:embedding_version`. Vectors from
different keys are never compared, so changing a deployment rebuilds cleanly
instead of silently mixing vector spaces.

### Audit and observability

| Collection | Key | Notes |
| --- | --- | --- |
| `audit_events` | `user_id`, `request_id` | Who did what, when, from which request |
| `agent_runs` | `user_id`, `agent_id` | One per orchestrated turn; no message content |
| `tool_invocations` | `run_id` | Tool, success, duration, selection reason |
| `ai_usage_records` | `occurred_at` | Tokens and cost by deployment/feature/agent; no customer data |

---

## 3. Ownership and isolation

Every collection holding customer data is indexed with the owner key **first**,
and every query filters on it:

```python
await self._accounts.find_one({"_id": account_id, "user_id": user_id})
```

Not "load, then check". The filter is the isolation boundary; the check is the
second line of defence. `test_user_owned_collections_are_indexed_by_owner_first`
asserts every non-shared collection has an owner-scoped index, so this stays
cheap as data grows.

Shared collections (`users`, knowledge, embedding cache, `ai_usage_records`)
are exempt because they hold no per-customer data — usage records deliberately
carry only deployment/feature/agent attribution.

---

## 4. Money in documents

```json
{
  "balance_minor_units": 250000,
  "currency": "RON"
}
```

Integer minor units plus an ISO currency code. No `Decimal128`, no doubles, no
formatted strings. Formatting happens in the frontend; arithmetic happens in
`libra.core.money`.

---

## 5. Indexes

Declared once, in code, as data:

```python
IndexSpec("transactions",
          (("user_id", 1), ("account_id", 1), ("booked_at", -1)),
          "transactions_user_account_date")
```

Notable ones:

* `payments_idempotency_unique` — the database, not the application, is what
  guarantees a retried transfer executes once.
* `accounts_user_iban` (unique per user) — no duplicate account rows.
* `embedding_cache_ttl` — cached vectors expire after 30 days; a cache is not
  an archive.
* `knowledge_chunks_embedding_chunk` (unique) — one vector per chunk per
  embedding space.
* `ai_messages_user_conversation_seq` — the ordering the recent-window and
  compression queries rely on.

---

## 6. Transactions and consistency

Today's write paths are single-document and idempotent by key. When real money
movement arrives (Phase 5+), the options are, in order of preference:

1. keep the operation single-document (preferred — a transfer between two
   accounts of the same user can be modelled as one ledger document);
2. MongoDB multi-document transactions on a replica set;
3. a dedicated transactional store for the ledger.

Option 3 stays open precisely because services depend on repository interfaces.
Replacing `AccountRepository`'s implementation does not touch a single service,
router, tool or agent.

---

## 7. Lifecycle

| Data | Policy |
| --- | --- |
| Banking records | Retained per regulation; never hard-deleted by user action |
| Conversations and messages | User-deletable; deletion removes summaries and memories too |
| User memories | Expire via `expires_at`; refreshed only by continued relevance |
| Embedding cache | 30-day TTL |
| Uploaded documents | User-deletable; deletion must also drop `document_chunks` |
| Audit events | Append-only; never edited or deleted by application code |
| Agent runs / usage | Retained for analysis; contain no customer content |

Account closure and GDPR erasure are a Phase 6 workflow: banking records are
retained under regulatory obligation while conversation state, memories,
documents and their chunks are removed. The separation of the four state
families is what makes that possible without a data archaeology project.
