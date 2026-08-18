"""Declarative MongoDB index specifications.

Indexes are declared here (not scattered across repositories) so that:

* the ownership rule is auditable — every collection holding customer data is
  indexed by ``user_id`` first, which is also how queries must be written;
* ``libra indexes`` can apply them at deploy time;
* ``tests/test_persistence_indexes.py`` can assert the invariants.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Collections that do not hold per-user data and are therefore exempt from
#: the ``user_id``-first rule. ``ai_usage_records`` is aggregate cost telemetry
#: (deployment, feature, agent) and deliberately carries no customer data.
SHARED_COLLECTIONS = frozenset(
    {
        "users",
        "knowledge_documents",
        "knowledge_chunks",
        "embedding_cache",
        "merchants",
        "ai_usage_records",
    }
)


@dataclass(frozen=True)
class IndexSpec:
    collection: str
    #: Ordered ``(field, direction)`` pairs; direction is 1 or -1.
    keys: tuple[tuple[str, int], ...]
    name: str
    unique: bool = False
    #: Seconds after which documents expire (TTL indexes only).
    expire_after_seconds: int | None = None
    partial_filter: dict[str, object] = field(default_factory=dict)


INDEX_SPECS: tuple[IndexSpec, ...] = (
    # -- authoritative banking state -------------------------------------
    IndexSpec("users", (("email", 1),), "users_email_unique", unique=True),
    IndexSpec("accounts", (("user_id", 1), ("status", 1)), "accounts_user_status"),
    IndexSpec("accounts", (("user_id", 1), ("iban", 1)), "accounts_user_iban", unique=True),
    IndexSpec(
        "subaccounts", (("user_id", 1), ("account_id", 1)), "subaccounts_user_account"
    ),
    IndexSpec(
        "transactions",
        (("user_id", 1), ("account_id", 1), ("booked_at", -1)),
        "transactions_user_account_date",
    ),
    IndexSpec(
        "transactions",
        (("user_id", 1), ("merchant_key", 1), ("booked_at", -1)),
        "transactions_user_merchant_date",
    ),
    IndexSpec("payments", (("user_id", 1), ("created_at", -1)), "payments_user_created"),
    IndexSpec(
        "payments",
        (("idempotency_key", 1),),
        "payments_idempotency_unique",
        unique=True,
    ),
    IndexSpec("payment_groups", (("member_user_ids", 1),), "payment_groups_members"),
    IndexSpec("group_expenses", (("group_id", 1), ("created_at", -1)), "group_expenses_group"),
    IndexSpec("savings_goals", (("user_id", 1), ("status", 1)), "savings_goals_user_status"),
    IndexSpec(
        "allocation_rules", (("user_id", 1), ("trigger", 1)), "allocation_rules_user_trigger"
    ),
    IndexSpec("subscriptions", (("user_id", 1), ("state", 1)), "subscriptions_user_state"),
    IndexSpec(
        "financial_health_snapshots",
        (("user_id", 1), ("computed_at", -1)),
        "financial_health_user_date",
    ),
    # -- AI / conversation state -----------------------------------------
    IndexSpec(
        "ai_conversations",
        (("user_id", 1), ("updated_at", -1)),
        "ai_conversations_user_updated",
    ),
    IndexSpec(
        "ai_messages",
        (("user_id", 1), ("conversation_id", 1), ("sequence", 1)),
        "ai_messages_user_conversation_seq",
    ),
    IndexSpec(
        "ai_conversation_summaries",
        (("user_id", 1), ("conversation_id", 1)),
        "ai_summaries_user_conversation",
        unique=True,
    ),
    IndexSpec("ai_user_memories", (("user_id", 1), ("kind", 1)), "ai_memories_user_kind"),
    # -- documents and RAG ------------------------------------------------
    IndexSpec("documents", (("user_id", 1), ("uploaded_at", -1)), "documents_user_uploaded"),
    IndexSpec(
        "document_chunks",
        (("user_id", 1), ("document_id", 1), ("position", 1)),
        "document_chunks_user_document",
    ),
    IndexSpec(
        "knowledge_documents",
        (("document_id", 1), ("version", 1)),
        "knowledge_documents_id_version",
        unique=True,
    ),
    IndexSpec(
        "knowledge_chunks",
        (("embedding_key", 1), ("chunk_id", 1)),
        "knowledge_chunks_embedding_chunk",
        unique=True,
    ),
    IndexSpec(
        "knowledge_chunks",
        (("language", 1), ("document_type", 1)),
        "knowledge_chunks_filters",
    ),
    IndexSpec(
        "embedding_cache",
        (("cache_key", 1),),
        "embedding_cache_key_unique",
        unique=True,
    ),
    IndexSpec(
        "embedding_cache",
        (("created_at", 1),),
        "embedding_cache_ttl",
        expire_after_seconds=60 * 60 * 24 * 30,
    ),
    # -- audit and observability ------------------------------------------
    IndexSpec("audit_events", (("user_id", 1), ("occurred_at", -1)), "audit_events_user_date"),
    IndexSpec("audit_events", (("request_id", 1),), "audit_events_request"),
    IndexSpec("agent_runs", (("user_id", 1), ("started_at", -1)), "agent_runs_user_date"),
    IndexSpec("agent_runs", (("agent_id", 1), ("started_at", -1)), "agent_runs_agent_date"),
    IndexSpec("tool_invocations", (("run_id", 1),), "tool_invocations_run"),
    IndexSpec("ai_usage_records", (("occurred_at", -1),), "ai_usage_date"),
)


def collections() -> tuple[str, ...]:
    seen: list[str] = []
    for spec in INDEX_SPECS:
        if spec.collection not in seen:
            seen.append(spec.collection)
    return tuple(seen)
