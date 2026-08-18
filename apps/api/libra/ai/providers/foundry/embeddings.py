"""Microsoft Foundry embedding provider (text-embedding-3-small deployment)."""

from __future__ import annotations

from typing import Any, Sequence

from libra.ai.providers.base import EmbeddingBatch, TokenUsage
from libra.core.config import FoundrySettings
from libra.core.errors import AIProviderError, AIProviderUnavailableError, ValidationError


class MicrosoftFoundryEmbeddingProvider:
    name = "microsoft_foundry"

    def __init__(self, settings: FoundrySettings) -> None:
        self._settings = settings
        self._client: Any | None = None

    @property
    def deployment(self) -> str:
        return self._settings.embedding_deployment

    @property
    def embedding_key(self) -> str:
        """Identity of the vector space; stored alongside every vector."""
        return f"{self.name}:{self.deployment}:{self._settings.embedding_version}"

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

    async def embed(self, texts: Sequence[str]) -> EmbeddingBatch:
        cleaned = [text.strip() for text in texts]
        if not cleaned or any(not text for text in cleaned):
            raise ValidationError("Embedding input cannot be empty.")

        client = self._get_client()
        try:
            response = await client.embeddings.create(
                model=self.deployment, input=list(cleaned)
            )
        except Exception as error:  # noqa: BLE001 - normalized into a domain error
            raise AIProviderError("The embedding deployment returned an error.") from error

        usage = getattr(response, "usage", None)
        return EmbeddingBatch(
            vectors=tuple(
                tuple(float(value) for value in item.embedding) for item in response.data
            ),
            provider=self.name,
            deployment=self.deployment,
            embedding_version=self._settings.embedding_version,
            usage=TokenUsage(input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0)),
        )
