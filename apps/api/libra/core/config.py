"""Typed configuration loaded from environment variables.

Every deployment-specific value (Foundry endpoint, deployment names, Mongo URI,
retrieval defaults) is configuration, never a literal in business logic. See
``.env.example`` at the repository root for the full variable list.

Implementation note: settings are built from an explicit ``Mapping`` instead of
reading ``os.environ`` inside the models, so tests can construct any
environment without mutating the process.
"""

from __future__ import annotations

import functools
import os
from enum import Enum
from typing import Mapping

from pydantic import BaseModel, Field

from libra.core.errors import ConfigurationError


class Environment(str, Enum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def is_deployed(self) -> bool:
        return self in (Environment.STAGING, Environment.PRODUCTION)


class AppSettings(BaseModel):
    name: str = "Libra Galaxy API"
    environment: Environment = Environment.LOCAL
    api_prefix: str = "/api/v1"
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)


class MongoSettings(BaseModel):
    """MongoDB connection. Only repositories may use these values."""

    uri: str = "mongodb://localhost:27017"
    database: str = "libra_galaxy"
    #: ``memory`` keeps the in-process repositories used by tests and local
    #: development; ``mongo`` requires a reachable server.
    backend: str = Field(default="memory", pattern="^(memory|mongo)$")


class FoundrySettings(BaseModel):
    """Microsoft Foundry endpoint and deployment names."""

    endpoint: str = ""
    api_key: str = ""
    api_version: str = "2024-10-21"
    chat_deployment: str = "gpt-5-mini"
    embedding_deployment: str = "text-embedding-3-small"
    #: Bumped when a deployment changes in a way that invalidates embeddings.
    embedding_version: str = "v1"
    request_timeout_seconds: float = 30.0

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key)


class VoiceSettings(BaseModel):
    """Microsoft voice capability. Implementation intentionally undecided."""

    enabled: bool = False
    region: str = ""
    api_key: str = ""


class AISettings(BaseModel):
    max_output_tokens: int = 1500
    max_context_chars: int = 24_000
    tool_timeout_seconds: float = 15.0
    #: USD per million tokens for the configured chat deployment.
    input_price_per_million: float = 0.25
    cached_input_price_per_million: float = 0.025
    output_price_per_million: float = 2.00
    embedding_price_per_million: float = 0.02


class RagSettings(BaseModel):
    chunk_size_tokens: int = 320
    chunk_overlap_tokens: int = 60
    embedding_batch_size: int = 16
    retrieval_top_k: int = 5
    retrieval_min_score: float = 0.30
    max_retrieved_chars: int = 7000


class SecuritySettings(BaseModel):
    #: Header-based development principals. Refused outside local/test.
    dev_auth_enabled: bool = True
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 1_209_600


class ObservabilitySettings(BaseModel):
    log_level: str = "INFO"
    log_format: str = Field(default="json", pattern="^(json|console)$")
    #: When true (the default), message bodies are never written to telemetry.
    redact_conversation_content: bool = True


class Settings(BaseModel):
    app: AppSettings = AppSettings()
    mongo: MongoSettings = MongoSettings()
    foundry: FoundrySettings = FoundrySettings()
    voice: VoiceSettings = VoiceSettings()
    ai: AISettings = AISettings()
    rag: RagSettings = RagSettings()
    security: SecuritySettings = SecuritySettings()
    observability: ObservabilitySettings = ObservabilitySettings()

    def require_foundry(self) -> FoundrySettings:
        """Return Foundry settings or fail loudly. There is no fallback."""
        if not self.foundry.is_configured:
            raise ConfigurationError("Microsoft Foundry endpoint or API key is missing.")
        return self.foundry


def _bool(env: Mapping[str, str], key: str, default: bool) -> bool:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key)
    return int(raw) if raw else default


def _float(env: Mapping[str, str], key: str, default: float) -> float:
    raw = env.get(key)
    return float(raw) if raw else default


def _str(env: Mapping[str, str], key: str, default: str) -> str:
    raw = env.get(key)
    return raw.strip() if raw else default


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build settings from an environment mapping (defaults to ``os.environ``)."""
    env = os.environ if env is None else env

    environment = Environment(_str(env, "LIBRA_ENV", Environment.LOCAL.value))
    origins = tuple(
        origin.strip()
        for origin in _str(env, "LIBRA_CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    )

    settings = Settings(
        app=AppSettings(
            name=_str(env, "LIBRA_APP_NAME", "Libra Galaxy API"),
            environment=environment,
            api_prefix=_str(env, "LIBRA_API_PREFIX", "/api/v1"),
            cors_origins=origins,
        ),
        mongo=MongoSettings(
            uri=_str(env, "LIBRA_MONGO_URI", "mongodb://localhost:27017"),
            database=_str(env, "LIBRA_MONGO_DATABASE", "libra_galaxy"),
            backend=_str(env, "LIBRA_PERSISTENCE_BACKEND", "memory"),
        ),
        foundry=FoundrySettings(
            endpoint=_str(env, "LIBRA_FOUNDRY_ENDPOINT", ""),
            api_key=_str(env, "LIBRA_FOUNDRY_API_KEY", ""),
            api_version=_str(env, "LIBRA_FOUNDRY_API_VERSION", "2024-10-21"),
            chat_deployment=_str(env, "LIBRA_FOUNDRY_CHAT_DEPLOYMENT", "gpt-5-mini"),
            embedding_deployment=_str(
                env, "LIBRA_FOUNDRY_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
            ),
            embedding_version=_str(env, "LIBRA_EMBEDDING_VERSION", "v1"),
            request_timeout_seconds=_float(env, "LIBRA_FOUNDRY_TIMEOUT_SECONDS", 30.0),
        ),
        voice=VoiceSettings(
            enabled=_bool(env, "LIBRA_VOICE_ENABLED", False),
            region=_str(env, "LIBRA_VOICE_REGION", ""),
            api_key=_str(env, "LIBRA_VOICE_API_KEY", ""),
        ),
        ai=AISettings(
            max_output_tokens=_int(env, "LIBRA_AI_MAX_OUTPUT_TOKENS", 1500),
            max_context_chars=_int(env, "LIBRA_AI_MAX_CONTEXT_CHARS", 24_000),
            tool_timeout_seconds=_float(env, "LIBRA_AI_TOOL_TIMEOUT_SECONDS", 15.0),
            input_price_per_million=_float(env, "LIBRA_AI_INPUT_PRICE_PER_MILLION", 0.25),
            cached_input_price_per_million=_float(
                env, "LIBRA_AI_CACHED_INPUT_PRICE_PER_MILLION", 0.025
            ),
            output_price_per_million=_float(env, "LIBRA_AI_OUTPUT_PRICE_PER_MILLION", 2.00),
            embedding_price_per_million=_float(
                env, "LIBRA_AI_EMBEDDING_PRICE_PER_MILLION", 0.02
            ),
        ),
        rag=RagSettings(
            chunk_size_tokens=_int(env, "LIBRA_RAG_CHUNK_SIZE_TOKENS", 320),
            chunk_overlap_tokens=_int(env, "LIBRA_RAG_CHUNK_OVERLAP_TOKENS", 60),
            embedding_batch_size=_int(env, "LIBRA_RAG_EMBEDDING_BATCH_SIZE", 16),
            retrieval_top_k=_int(env, "LIBRA_RAG_TOP_K", 5),
            retrieval_min_score=_float(env, "LIBRA_RAG_MIN_SCORE", 0.30),
            max_retrieved_chars=_int(env, "LIBRA_RAG_MAX_RETRIEVED_CHARS", 7000),
        ),
        security=SecuritySettings(
            dev_auth_enabled=_bool(env, "LIBRA_DEV_AUTH_ENABLED", not environment.is_deployed),
            access_token_ttl_seconds=_int(env, "LIBRA_ACCESS_TOKEN_TTL_SECONDS", 900),
            refresh_token_ttl_seconds=_int(env, "LIBRA_REFRESH_TOKEN_TTL_SECONDS", 1_209_600),
        ),
        observability=ObservabilitySettings(
            log_level=_str(env, "LIBRA_LOG_LEVEL", "INFO").upper(),
            log_format=_str(env, "LIBRA_LOG_FORMAT", "json"),
            redact_conversation_content=_bool(env, "LIBRA_REDACT_CONVERSATION_CONTENT", True),
        ),
    )

    _validate(settings)
    return settings


def _validate(settings: Settings) -> None:
    """Reject configurations that would be unsafe in a deployed environment."""
    if settings.app.environment.is_deployed:
        if settings.security.dev_auth_enabled:
            raise ConfigurationError(
                "Development authentication cannot be enabled outside local/test."
            )
        if settings.mongo.backend != "mongo":
            raise ConfigurationError(
                "In-memory persistence cannot be used in a deployed environment."
            )
    if settings.rag.chunk_overlap_tokens >= settings.rag.chunk_size_tokens:
        raise ConfigurationError("RAG chunk overlap must be smaller than the chunk size.")


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings, resolved once from ``os.environ``."""
    return load_settings()
