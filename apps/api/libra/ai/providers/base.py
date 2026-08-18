"""Provider interfaces.

These exist for modularity and testability — *not* for fallback. Libra Galaxy
has exactly one implementation of each interface today (Microsoft Foundry). If
Foundry is unavailable the operation fails with
``AI_PROVIDER_UNAVAILABLE``; it never silently switches provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, Sequence, runtime_checkable


class ChatRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class ChatMessage:
    role: ChatRole
    content: str


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "output_tokens": self.output_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(frozen=True)
class ChatCompletion:
    text: str
    provider: str
    deployment: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    finish_reason: str = "stop"


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: tuple[tuple[float, ...], ...]
    provider: str
    deployment: str
    #: Bumped when a deployment change invalidates previously stored vectors.
    embedding_version: str = "v1"
    usage: TokenUsage = field(default_factory=TokenUsage)

    @property
    def embedding_key(self) -> str:
        """Identity of the embedding space. Vectors are never mixed across keys."""
        return f"{self.provider}:{self.deployment}:{self.embedding_version}"


@runtime_checkable
class ChatProvider(Protocol):
    """Text generation."""

    name: str

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ChatCompletion: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Vector embeddings for RAG."""

    name: str
    embedding_key: str

    async def embed(self, texts: Sequence[str]) -> EmbeddingBatch: ...


@runtime_checkable
class VoiceProvider(Protocol):
    """Speech in and speech out.

    Voice is an interaction channel: transcripts enter the same orchestrator as
    typed messages. The concrete Microsoft implementation is deliberately not
    chosen yet, so this interface stays small.
    """

    name: str

    async def transcribe(self, audio: bytes, *, locale: str) -> str: ...

    async def synthesize(self, text: str, *, locale: str) -> bytes: ...
