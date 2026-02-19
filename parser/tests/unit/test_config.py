import pytest
from unittest.mock import patch

from config import Settings, get_settings


VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def _make_settings(**kwargs):
    """Create Settings with env file loading disabled."""
    return Settings(_env_file=None, **kwargs)


@pytest.mark.parametrize("level", VALID_LOG_LEVELS)
def test_validate_log_level_valid_values(level):
    settings = _make_settings(log_level=level, openrouter_api_key="sk-or-test123")

    assert settings.log_level == level


@pytest.mark.parametrize("level", ["debug", "info", "Warning", "error", "CrItIcAl"])
def test_validate_log_level_case_insensitive(level):
    settings = _make_settings(log_level=level, openrouter_api_key="sk-or-test123")

    assert settings.log_level == level.upper()


def test_validate_log_level_invalid_raises_value_error():
    with pytest.raises(ValueError, match="Invalid log level"):
        _make_settings(log_level="TRACE", openrouter_api_key="sk-or-test123")


def test_validate_openrouter_api_key_valid():
    settings = _make_settings(openrouter_api_key="sk-or-abc123")

    assert settings.openrouter_api_key == "sk-or-abc123"


def test_validate_openrouter_api_key_invalid_prefix_raises_value_error():
    with pytest.raises(ValueError, match="must start with 'sk-or-'"):
        _make_settings(openrouter_api_key="sk-abc")


def test_get_settings_returns_singleton():
    mock_settings = _make_settings(openrouter_api_key="sk-or-test123")
    with patch("config._settings", mock_settings):
        first = get_settings()
        second = get_settings()

    assert first is second


def test_get_settings_creates_instance_when_none():
    mock_instance = _make_settings(openrouter_api_key="sk-or-test123")
    with (
        patch("config._settings", None),
        patch("config.Settings", return_value=mock_instance) as mock_cls,
    ):
        result = get_settings()

    mock_cls.assert_called_once()
    assert result is mock_instance
