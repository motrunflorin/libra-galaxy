"""Conversation persistence contract. Every method is user-scoped."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from libra.ai.conversations.models import Conversation, ConversationSummary, Message


class ConversationRepository(ABC):
    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation: ...

    @abstractmethod
    async def get_for_user(self, user_id: str, conversation_id: str) -> Conversation | None: ...

    @abstractmethod
    async def list_for_user(self, user_id: str, *, limit: int = 20) -> Sequence[Conversation]: ...

    @abstractmethod
    async def append_message(self, message: Message) -> Message: ...

    @abstractmethod
    async def recent_messages(
        self, user_id: str, conversation_id: str, *, limit: int
    ) -> Sequence[Message]: ...

    @abstractmethod
    async def messages_after(
        self, user_id: str, conversation_id: str, *, sequence: int, limit: int
    ) -> Sequence[Message]: ...

    @abstractmethod
    async def get_summary(
        self, user_id: str, conversation_id: str
    ) -> ConversationSummary | None: ...

    @abstractmethod
    async def save_summary(self, summary: ConversationSummary) -> ConversationSummary: ...
