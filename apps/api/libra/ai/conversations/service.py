"""Conversation application service.

Improvements over the reference project's session store:

* every operation takes a ``Principal`` and is scoped to that user;
* compression is incremental — a watermark records how far the summary
  reaches, so a turn never re-reads the whole history;
* the summary is produced by a deterministic compressor by default. An
  LLM-written summary can be plugged in later without changing the storage
  model, and a model failure degrades to the deterministic path rather than
  losing context.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from libra.ai.conversations.models import (
    Channel,
    Conversation,
    ConversationSummary,
    Message,
    MessageRole,
)
from libra.ai.conversations.repository import ConversationRepository
from libra.core.errors import ResourceNotFoundError
from libra.core.locale import Locale
from libra.core.security.authorization import require_permission
from libra.core.security.principal import Permission, Principal

#: Turns kept verbatim in context; older turns live in the summary.
RECENT_MESSAGE_LIMIT = 12
MAX_SUMMARY_CHARS = 3_000
_COMPRESS_BATCH = 50


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ConversationService:
    def __init__(self, repository: ConversationRepository) -> None:
        self._repository = repository

    async def start(self, principal: Principal, *, locale: Locale) -> Conversation:
        require_permission(principal, Permission.ASSISTANT_USE)
        conversation = Conversation(
            conversation_id=f"cnv_{uuid.uuid4().hex[:16]}",
            user_id=principal.user_id,
            locale=locale,
            created_at=_now(),
            updated_at=_now(),
        )
        return await self._repository.create(conversation)

    async def get(self, principal: Principal, conversation_id: str) -> Conversation:
        require_permission(principal, Permission.ASSISTANT_USE)
        conversation = await self._repository.get_for_user(principal.user_id, conversation_id)
        if conversation is None:
            raise ResourceNotFoundError()
        return conversation

    async def append(
        self,
        principal: Principal,
        conversation_id: str,
        *,
        role: MessageRole,
        content: str,
        channel: Channel = Channel.TEXT,
        agent_id: str = "",
    ) -> Message:
        conversation = await self.get(principal, conversation_id)
        existing = await self._repository.recent_messages(
            principal.user_id, conversation.conversation_id, limit=1
        )
        next_sequence = (existing[-1].sequence + 1) if existing else 1

        return await self._repository.append_message(
            Message(
                message_id=f"msg_{uuid.uuid4().hex[:16]}",
                conversation_id=conversation.conversation_id,
                user_id=principal.user_id,
                role=role,
                content=content,
                sequence=next_sequence,
                created_at=_now(),
                channel=channel,
                agent_id=agent_id,
            )
        )

    async def recent_messages(
        self, principal: Principal, conversation_id: str, *, limit: int = RECENT_MESSAGE_LIMIT
    ) -> Sequence[Message]:
        await self.get(principal, conversation_id)
        return await self._repository.recent_messages(
            principal.user_id, conversation_id, limit=limit
        )

    async def summary(
        self, principal: Principal, conversation_id: str
    ) -> ConversationSummary | None:
        await self.get(principal, conversation_id)
        return await self._repository.get_summary(principal.user_id, conversation_id)

    async def compress(
        self, principal: Principal, conversation_id: str
    ) -> ConversationSummary | None:
        """Fold messages older than the recent window into the summary.

        Only messages above the stored watermark are read, so cost per turn
        stays constant regardless of conversation length.
        """
        conversation = await self.get(principal, conversation_id)
        existing = await self._repository.get_summary(principal.user_id, conversation_id)
        watermark = existing.covers_up_to_sequence if existing else 0

        recent = await self._repository.recent_messages(
            principal.user_id, conversation_id, limit=RECENT_MESSAGE_LIMIT
        )
        if not recent:
            return existing

        oldest_kept_sequence = recent[0].sequence
        if oldest_kept_sequence <= watermark + 1:
            return existing

        pending = await self._repository.messages_after(
            principal.user_id, conversation_id, sequence=watermark, limit=_COMPRESS_BATCH
        )
        to_fold = [message for message in pending if message.sequence < oldest_kept_sequence]
        if not to_fold:
            return existing

        merged = self._compress_text(existing.content if existing else "", to_fold)
        summary = ConversationSummary(
            conversation_id=conversation.conversation_id,
            user_id=principal.user_id,
            content=merged,
            covers_up_to_sequence=to_fold[-1].sequence,
            updated_at=_now(),
        )
        return await self._repository.save_summary(summary)

    @staticmethod
    def _compress_text(existing: str, messages: Sequence[Message]) -> str:
        """Deterministic compression: one condensed line per folded turn.

        No model call, no hidden state — the result is reproducible and cheap.
        Replacing this with an LLM summariser is a single-method change.
        """
        lines = [existing] if existing else []
        for message in messages:
            condensed = " ".join(message.content.split())
            if len(condensed) > 220:
                condensed = condensed[:217] + "..."
            lines.append(f"{message.role.value}: {condensed}")
        return "\n".join(lines)[-MAX_SUMMARY_CHARS:]
