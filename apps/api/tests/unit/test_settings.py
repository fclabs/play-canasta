from __future__ import annotations

import pytest
from pydantic import ValidationError

from canasta_api.settings import Settings

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("LOG_LEVEL", "APP_ENV", "WEB_DIST_DIR"):
        monkeypatch.delenv(var, raising=False)


def test_settings_use_defaults_when_env_is_unset():
    # Given no relevant environment variables
    # When settings are loaded
    settings = Settings(_env_file=None)

    # Then defaults apply
    assert settings.log_level == "INFO"
    assert settings.app_env == "local"
    assert settings.web_dist_dir is None


def test_settings_read_values_from_environment(monkeypatch: pytest.MonkeyPatch):
    # Given
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("APP_ENV", "preview")
    monkeypatch.setenv("WEB_DIST_DIR", "/tmp/dist")

    # When
    settings = Settings(_env_file=None)

    # Then
    assert settings.log_level == "DEBUG"
    assert settings.app_env == "preview"
    assert str(settings.web_dist_dir) == "/tmp/dist"


def test_settings_reject_invalid_log_level_naming_the_variable(
    monkeypatch: pytest.MonkeyPatch,
):
    # Given
    monkeypatch.setenv("LOG_LEVEL", "VERBOSE")

    # When / Then
    with pytest.raises(ValidationError, match="LOG_LEVEL"):
        Settings(_env_file=None)


def test_settings_reject_invalid_app_env_naming_the_variable(
    monkeypatch: pytest.MonkeyPatch,
):
    # Given
    monkeypatch.setenv("APP_ENV", "staging")

    # When / Then
    with pytest.raises(ValidationError, match="APP_ENV"):
        Settings(_env_file=None)
