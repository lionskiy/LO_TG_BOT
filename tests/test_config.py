"""Tests for bot.config."""
import pytest

from bot import config


def test_validate_config_missing_bot_token(monkeypatch):
    monkeypatch.setattr(config, "BOT_TOKEN", None)
    monkeypatch.setattr(
        config, "get_active_llm", lambda: ("openai", "gpt-4o-mini", {"api_key": "sk-test"})
    )
    with pytest.raises(ValueError, match="BOT_TOKEN"):
        config.validate_config()


def test_validate_config_no_llm_provider(monkeypatch):
    monkeypatch.setattr(config, "BOT_TOKEN", "123:abc")
    monkeypatch.setattr(config, "_cached_llm", None)

    def raise_no_llm():
        raise ValueError("No LLM provider configured.")

    monkeypatch.setattr(config, "get_active_llm", raise_no_llm)
    with pytest.raises(ValueError, match="No LLM provider"):
        config.validate_config()


def test_validate_config_ok(monkeypatch):
    monkeypatch.setattr(config, "BOT_TOKEN", "123:abc")
    monkeypatch.setattr(
        config, "get_active_llm", lambda: ("openai", "gpt-4o-mini", {"api_key": "sk-test"})
    )
    config.validate_config()
