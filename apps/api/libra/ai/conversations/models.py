"""Conversation models.

Every conversation and message carries ``user_id``. Unlike the reference
project — where any client-supplied ``session_id`` reached any session — a
conversation here is a user-owned resource and every read is scoped by owner.

Conversation content is *recollection*, never authoritative banking state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from libra.core.locale import DEFAULT_LOCALE, Locale


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Channel(str, Enum):
    """How the turn arrived. Voice reuses the same orchestrator as text."""

    TEXT = "text"
    VOICE = "voice"


@dataclass(frozen=True)
class Conversation:
    conversation_id: str
    user_id: str
    title: str = ""
    locale: Locale = DEFAULT_LOCALE
    created_at: datetime | None = None
    updated_at: datetime | None = None
    #: Sequence number up to which content is folded into the summary.
    summary_watermark: int = 0


@dataclass(frozen=True)
class Message:
    message_id: str
    conversation_id: str
    user_id: str
    role: MessageRole
    content: str
    sequence: int
    created_at: datetime | None = None
    channel: Channel = Channel.TEXT
    #: Agent that produced an assistant message; empty for user messages.
    agent_id: str = ""


@dataclass(frozen=True)
class ConversationSummary:
    """Compressed older turns.

    Stored separately from messages so compression never rewrites what the
    user actually said, and so the watermark makes compression incremental
    instead of re-reading the whole history every turn.
    """

    conversation_id: str
    user_id: str
    content: str
    covers_up_to_sequence: int
    updated_at: datetime | None = None
