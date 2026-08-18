"""Index declarations and log redaction — the data-governance invariants."""

from __future__ import annotations

import json
import logging

from libra.core.logging import JsonFormatter, redact
from libra.core.persistence.indexes import INDEX_SPECS, SHARED_COLLECTIONS, collections
from libra.core.request_context import set_request_id, set_user_id


def test_index_names_are_unique() -> None:
    names = [spec.name for spec in INDEX_SPECS]
    assert len(names) == len(set(names))


def test_user_owned_collections_are_indexed_by_owner_first() -> None:
    """Isolation is only cheap if every query can filter on ``user_id`` first."""
    for collection in collections():
        if collection in SHARED_COLLECTIONS:
            continue
        specs = [spec for spec in INDEX_SPECS if spec.collection == collection]
        owner_first = [
            spec
            for spec in specs
            if spec.keys[0][0] in {"user_id", "member_user_ids", "group_id", "run_id"}
        ]
        assert owner_first, f"{collection} has no owner-scoped index"


def test_payments_are_idempotent_by_declaration() -> None:
    idempotency = [
        spec
        for spec in INDEX_SPECS
        if spec.collection == "payments" and spec.keys[0][0] == "idempotency_key"
    ]
    assert idempotency and idempotency[0].unique is True


def test_embedding_cache_expires() -> None:
    ttl = [
        spec
        for spec in INDEX_SPECS
        if spec.collection == "embedding_cache" and spec.expire_after_seconds
    ]
    assert ttl, "cached embeddings must not be retained forever"


def test_the_four_state_families_are_all_declared() -> None:
    declared = set(collections())
    assert {"accounts", "transactions", "payments"} <= declared  # banking
    assert {"ai_conversations", "ai_messages", "ai_user_memories"} <= declared  # AI state
    assert {"knowledge_chunks", "documents"} <= declared  # RAG / documents
    assert {"audit_events", "agent_runs"} <= declared  # audit and observability


def test_sensitive_fields_are_redacted() -> None:
    clean = redact(
        {
            "user_id": "usr_alice",
            "password": "hunter2",
            "nested": {"api_key": "secret", "count": 3},
            "items": [{"iban": "RO49AAAA", "ok": True}],
        }
    )

    assert clean["user_id"] == "usr_alice"
    assert clean["password"] == "[redacted]"
    assert clean["nested"]["api_key"] == "[redacted]"
    assert clean["nested"]["count"] == 3
    assert clean["items"][0]["iban"] == "[redacted]"


def test_log_records_carry_correlation_ids_and_no_message_content() -> None:
    set_request_id("req_test")
    set_user_id("usr_alice")

    record = logging.LogRecord(
        name="libra.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="tool.executed",
        args=(),
        exc_info=None,
    )
    record.event_data = {"tool": "get_accounts", "content": "my balance is 2500 RON"}

    payload = json.loads(JsonFormatter().format(record))

    assert payload["request_id"] == "req_test"
    assert payload["user_id"] == "usr_alice"
    assert payload["tool"] == "get_accounts"
    assert payload["content"] == "[redacted]"

    set_request_id(None)
    set_user_id(None)
