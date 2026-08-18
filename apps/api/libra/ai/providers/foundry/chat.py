"""Microsoft Foundry chat provider (GPT-5 mini deployment).

The deployment name comes from configuration; it is never hard-coded in
business logic. Failures surface as ``AIProviderUnavailableError`` /
``AIProviderError`` — there is no fallback provider.
"""

from __future__ import annotations

import time
from typing import Any, Sequence

from libra.ai.providers.base import ChatCompletion, ChatMessage, TokenUsage
from libra.core.config import FoundrySettings
from libra.core.errors import AIProviderError, AIProviderUnavailableError


class MicrosoftFoundryChatProvider:
    name = "microsoft_foundry"

    def __init__(self, settings: FoundrySettings, *, max_output_tokens: int = 1500) -> None:
        self._settings = settings
        self._max_output_tokens = max_output_tokens
        self._client: Any | None = None

    @property
    def deployment(self) -> str:
        return self._settings.chat_deployment

    def _get_client(self) -> Any:
        if not self._settings.is_configured:
            raise AIProviderUnavailableError("Microsoft Foundry is not configured.")
        if self._client is None:
            try:
                from openai import AsyncAzureOpenAI
            except ImportError as error:  # pragma: no cover - depends on install
                raise AIProviderUnavailableError(
                    "The Azure OpenAI client library is not installed."
                ) from error
            self._client = AsyncAzureOpenAI(
                azure_endpoint=self._settings.endpoint,
                api_key=self._settings.api_key,
                api_version=self._settings.api_version,
                timeout=self._settings.request_timeout_seconds,
            )
        return self._client

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ChatCompletion:
        client = self._get_client()
        payload = [{"role": message.role.value, "content": message.content} for message in messages]
        started = time.perf_counter()

        try:
            response = await client.chat.completions.create(
                model=self.deployment,
                messages=payload,
                max_completion_tokens=max_output_tokens or self._max_output_tokens,
            )
        except Exception as error:  # noqa: BLE001 - normalized into a domain error
            raise AIProviderError("The chat deployment returned an error.") from error

        choice = response.choices[0]
        usage = getattr(response, "usage", None)
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        completion_details = getattr(usage, "completion_tokens_details", None)

        return ChatCompletion(
            text=choice.message.content or "",
            provider=self.name,
            deployment=self.deployment,
            usage=TokenUsage(
                input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
                cached_input_tokens=int(getattr(prompt_details, "cached_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
                reasoning_tokens=int(getattr(completion_details, "reasoning_tokens", 0) or 0),
            ),
            latency_ms=(time.perf_counter() - started) * 1000,
            finish_reason=str(getattr(choice, "finish_reason", "stop")),
        )
