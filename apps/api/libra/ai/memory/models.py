"""User memory models.

The reference project shared "cross-session memory" between all sessions of a
single-user app. In a multi-user bank that pattern leaks data, so memory here
is:

* always scoped to one ``user_id`` and never read across users;
* typed by ``kind``, so a durable preference is not confused with a passing
  conversational fact;
* explicitly *not* banking state — a remembered "I want to save 500 RON" is a
  preference, while the actual savings balance comes from AccountService.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MemoryKind(str, Enum):
    #: Stable, user-confirmed preference (tone, language, notification style).
    PREFERENCE = "preference"
    #: A goal or intention the user stated, pending deterministic setup.
    STATED_INTENT = "stated_intent"
    #: Useful conversational fact worth recalling in later sessions.
    CONVERSATIONAL_FACT = "conversational_fact"


@dataclass(frozen=True)
class UserMemory:
    memory_id: str
    user_id: str
    kind: MemoryKind
    content: str
    #: Conversation this memory was learned in, for auditability.
    origin_conversation_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    #: Memories expire unless refreshed, so stale recollections fade out.
    expires_at: datetime | None = None

    @property
    def is_authoritative_banking_state(self) -> bool:
        """Always false. Present so the rule is impossible to overlook."""
        return False
