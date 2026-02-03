"""Tests for bot.config."""
import pytest

from bot import config


def test_validate_config_missing_bot_token(monkeypatch):
    monkeypatch.setattr(config, "BOT_TOKEN", None)
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-test")
    with pytest.raises(ValueError, match="BOT_TOKEN"):
        config.validate_config()


def test_validate_config_missing_openai_key(monkeypatch):
    monkeypatch.setattr(config, "BOT_TOKEN", "123:abc")
    monkeypatch.setattr(config, "OPENAI_API_KEY", None)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        config.validate_config()


def test_validate_config_ok(monkeypatch):
    monkeypatch.setattr(config, "BOT_TOKEN", "123:abc")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-test")
    config.validate_config()
