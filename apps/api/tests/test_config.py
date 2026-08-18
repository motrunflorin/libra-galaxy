"""Configuration must fail loudly on unsafe deployment settings."""

from __future__ import annotations

import pytest

from libra.core.config import Environment, load_settings
from libra.core.errors import ConfigurationError


def test_defaults_carry_no_credentials() -> None:
    settings = load_settings({})
    assert settings.foundry.api_key == ""
    assert settings.foundry.is_configured is False


def test_deployment_names_come_from_configuration() -> None:
    settings = load_settings({"LIBRA_FOUNDRY_CHAT_DEPLOYMENT": "gpt-5-mini-eu"})
    assert settings.foundry.chat_deployment == "gpt-5-mini-eu"


def test_dev_auth_defaults_off_in_deployed_environments() -> None:
    settings = load_settings(
        {
            "LIBRA_ENV": "production",
            "LIBRA_PERSISTENCE_BACKEND": "mongo",
        }
    )
    assert settings.app.environment is Environment.PRODUCTION
    assert settings.security.dev_auth_enabled is False


def test_dev_auth_cannot_be_forced_on_in_production() -> None:
    with pytest.raises(ConfigurationError):
        load_settings(
            {
                "LIBRA_ENV": "production",
                "LIBRA_PERSISTENCE_BACKEND": "mongo",
                "LIBRA_DEV_AUTH_ENABLED": "true",
            }
        )


def test_in_memory_persistence_is_rejected_in_production() -> None:
    with pytest.raises(ConfigurationError):
        load_settings({"LIBRA_ENV": "production"})


def test_require_foundry_fails_without_credentials() -> None:
    with pytest.raises(ConfigurationError):
        load_settings({}).require_foundry()


def test_chunk_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ConfigurationError):
        load_settings(
            {"LIBRA_RAG_CHUNK_SIZE_TOKENS": "100", "LIBRA_RAG_CHUNK_OVERLAP_TOKENS": "100"}
        )
