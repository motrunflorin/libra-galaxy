"""In-process conversation repository for local development and tests."""

from __future__ import annotations

from typing import Sequence

from libra.ai.conversations.models import Conversation, ConversationSummary, Message
from libra.ai.conversations.repository import ConversationRepository


class InMemoryConversationRepository(ConversationRepository):
    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._messages: list[Message] = []
        self._summaries: dict[str, ConversationSummary] = {}

    async def create(self, conversation: Conversation) -> Conversation:
        self._conversations[conversation.conversation_id] = conversation
        return conversation

    async def get_for_user(self, user_id: str, conversation_id: str) -> Conversation | None:
        conversation = self._conversations.get(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            return None
        return conversation

    async def list_for_user(self, user_id: str, *, limit: int = 20) -> Sequence[Conversation]:
        owned = [item for item in self._conversations.values() if item.user_id == user_id]
        return owned[:limit]

    async def append_message(self, message: Message) -> Message:
        self._messages.append(message)
        return message

    async def recent_messages(
        self, user_id: str, conversation_id: str, *, limit: int
    ) -> Sequence[Message]:
        owned = [
            message
            for message in self._messages
            if message.user_id == user_id and message.conversation_id == conversation_id
        ]
        owned.sort(key=lambda message: message.sequence)
        return owned[-limit:]

    async def messages_after(
        self, user_id: str, conversation_id: str, *, sequence: int, limit: int
    ) -> Sequence[Message]:
        owned = [
            message
            for message in self._messages
            if message.user_id == user_id
            and message.conversation_id == conversation_id
            and message.sequence > sequence
        ]
        owned.sort(key=lambda message: message.sequence)
        return owned[:limit]

    async def get_summary(
        self, user_id: str, conversation_id: str
    ) -> ConversationSummary | None:
        summary = self._summaries.get(conversation_id)
        if summary is None or summary.user_id != user_id:
            return None
        return summary

    async def save_summary(self, summary: ConversationSummary) -> ConversationSummary:
        self._summaries[summary.conversation_id] = summary
        return summary
