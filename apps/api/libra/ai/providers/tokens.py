"""Token counting and cost estimation.

Adapted from the reference project's token counter: ``tiktoken`` when
available, a deterministic character heuristic otherwise, so cost tracking
still works in environments without the optional dependency.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from libra.ai.providers.base import ChatMessage, TokenUsage
from libra.core.config import AISettings


class TokenCounter:
    """Estimates prompt size before a call, for budgeting and telemetry."""

    def __init__(self, encoding_name: str = "o200k_base") -> None:
        self._encoding = None
        try:
            import tiktoken

            self._encoding = tiktoken.get_encoding(encoding_name)
        except Exception:  # pragma: no cover - optional dependency
            self._encoding = None

    def count_text(self, text: str) -> int:
        if not text:
            return 0
        if self._encoding is not None:
            try:
                return len(self._encoding.encode(text))
            except Exception:  # pragma: no cover - defensive
                pass
        return max(1, math.ceil(len(text) / 4))

    def count_messages(self, messages: Sequence[ChatMessage]) -> int:
        total = 2
        for message in messages:
            total += 4 + self.count_text(message.role.value) + self.count_text(message.content)
        return total


@dataclass(frozen=True)
class CostEstimate:
    """Estimated spend for one model call, in USD."""

    input_usd: float
    output_usd: float

    @property
    def total_usd(self) -> float:
        return self.input_usd + self.output_usd

    def to_dict(self) -> dict[str, float]:
        return {
            "input_usd": round(self.input_usd, 8),
            "output_usd": round(self.output_usd, 8),
            "total_usd": round(self.total_usd, 8),
        }


def estimate_chat_cost(usage: TokenUsage, settings: AISettings) -> CostEstimate:
    """Price a completion using the configured per-million rates."""
    cached = min(usage.cached_input_tokens, usage.input_tokens)
    uncached = usage.input_tokens - cached
    input_usd = (
        uncached * settings.input_price_per_million
        + cached * settings.cached_input_price_per_million
    ) / 1_000_000
    output_usd = usage.output_tokens * settings.output_price_per_million / 1_000_000
    return CostEstimate(input_usd=input_usd, output_usd=output_usd)


def estimate_embedding_cost(usage: TokenUsage, settings: AISettings) -> CostEstimate:
    input_usd = usage.input_tokens * settings.embedding_price_per_million / 1_000_000
    return CostEstimate(input_usd=input_usd, output_usd=0.0)
