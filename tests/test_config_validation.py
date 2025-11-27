import logging

import pytest

from app.config_validation import validate_settings


class DummySettings:
    """Lightweight settings stub so we don't depend on env values."""

    def __init__(
        self,
        env="development",
        supabase_url=None,
        supabase_key=None,
        supabase_anon=None,
        mistral=None,
        inworld=None,
        google=None,
    ):
        self.ENVIRONMENT = env
        self.SUPABASE_URL = supabase_url
        self.SUPABASE_KEY = supabase_key
        self.SUPABASE_ANON_KEY = supabase_anon
        self.MISTRAL_API_KEY = mistral
        self.INWORLD_API_KEY = inworld
        self.GOOGLE_API_KEY = google


def test_validate_settings_rejects_invalid_environment():
    settings = DummySettings(
        env="invalid", supabase_url="url", supabase_key="k", supabase_anon="a"
    )
    with pytest.raises(SystemExit) as excinfo:
        validate_settings(settings)
    assert "Invalid APP_ENV/ENVIRONMENT" in str(excinfo.value)


def test_validate_settings_requires_supabase_keys():
    settings = DummySettings(
        env="development", supabase_url=None, supabase_key=None, supabase_anon=None
    )
    with pytest.raises(SystemExit) as excinfo:
        validate_settings(settings)
    message = str(excinfo.value)
    assert "SUPABASE_URL" in message
    assert "SUPABASE_KEY" in message
    assert "SUPABASE_ANON_KEY" in message


def test_validate_settings_requires_prod_api_keys():
    settings = DummySettings(
        env="production",
        supabase_url="url",
        supabase_key="k",
        supabase_anon="a",
        mistral=None,
        inworld=None,
        google=None,
    )
    with pytest.raises(SystemExit) as excinfo:
        validate_settings(settings)
    assert "Production environment requires" in str(excinfo.value)
    assert "MISTRAL_API_KEY" in str(excinfo.value)


def test_validate_settings_warns_on_missing_optional_keys_in_dev(caplog):
    settings = DummySettings(
        env="development",
        supabase_url="url",
        supabase_key="k",
        supabase_anon="a",
    )
    caplog.set_level(logging.WARNING)
    validate_settings(settings)
    # Should warn for the optional production-only keys but not raise
    warnings = [rec for rec in caplog.records if rec.levelno >= logging.WARNING]
    assert warnings  # at least one warning emitted
