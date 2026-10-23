import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch

from restaurant_recommender.config import Settings


def test_settings_have_safe_development_defaults() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.app_env == "development"
    assert settings.app_port == 8000
    assert settings.llm_provider == "fake"
    assert settings.max_llm_candidates == 12


def test_managed_postgres_urls_select_installed_psycopg_driver() -> None:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        database_url="postgresql://user:password@database.example/app",
    )

    assert settings.database_url.startswith("postgresql+psycopg://")


def test_multiple_web_origins_are_normalized() -> None:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        web_origin="https://app.example/, https://preview.example",
    )

    assert settings.web_origin_list == ["https://app.example", "https://preview.example"]


def test_settings_read_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")

    settings = Settings()

    assert settings.app_env == "test"


def test_production_groq_requires_server_side_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(  # type: ignore[call-arg]
            _env_file=None,
            app_env="production",
            llm_provider="groq",
            llm_api_key=None,
        )
