"""Typed application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir="/run/secrets",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    web_origin: str = "http://localhost:5173"
    database_url: str = "postgresql+psycopg://nextleap:nextleap@localhost:5432/nextleap"
    redis_url: str = "redis://localhost:6379/0"
    redis_required: bool = False
    cache_recommendation_ttl_seconds: int = Field(default=300, ge=30, le=3600)
    cache_metadata_ttl_seconds: int = Field(default=900, ge=30, le=86400)
    recommendation_rate_limit: int = Field(default=20, ge=1, le=10000)
    metadata_rate_limit: int = Field(default=120, ge=1, le=10000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    max_request_body_bytes: int = Field(default=16_384, ge=1024, le=1_048_576)
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    trust_proxy_headers: bool = False
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    database_connect_timeout_seconds: int = Field(default=3, ge=1, le=30)
    graceful_shutdown_seconds: int = Field(default=20, ge=1, le=120)
    otel_exporter_otlp_endpoint: str | None = None
    telemetry_service_name: str = "nextleap-api"
    llm_provider: Literal["fake", "groq"] = "fake"
    llm_model: str = "deterministic-development-model"
    log_level: str = "INFO"
    ingestion_min_rows: int = Field(default=1, ge=1)
    ingestion_max_rejection_rate: float = Field(default=0.10, ge=0, le=1)
    ingestion_max_duplicate_rate: float = Field(default=0.20, ge=0, le=1)
    ingestion_min_location_coverage: float = Field(default=0.90, ge=0, le=1)
    ingestion_min_cuisine_coverage: float = Field(default=0.90, ge=0, le=1)
    max_filtered_records: int = Field(default=500, ge=1, le=5000)
    max_results: int = Field(default=10, ge=1, le=50)
    scoring_config_version: str = "score-v1"
    llm_api_key: str | None = None
    llm_timeout_seconds: float = Field(default=4.0, gt=0, le=30)
    max_llm_candidates: int = Field(default=12, ge=1, le=50)
    max_prompt_characters: int = Field(default=20_000, ge=1000, le=100_000)
    max_llm_output_tokens: int = Field(default=700, ge=100, le=4000)
    llm_reasoning_effort: Literal["low", "medium", "high"] = "low"
    active_prompt_version: str = "rank-v1"
    llm_circuit_failure_threshold: int = Field(default=3, ge=1, le=20)
    llm_circuit_cooldown_seconds: float = Field(default=30.0, gt=0, le=600)

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_driver(cls, value: object) -> object:
        """Use the installed psycopg 3 driver for common managed-Postgres URLs."""

        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @model_validator(mode="after")
    def validate_provider_secret(self) -> "Settings":
        if self.app_env == "production" and self.llm_provider == "groq" and not self.llm_api_key:
            raise ValueError("LLM_API_KEY is required for the Groq provider in production")
        if self.app_env == "production" and not self.redis_required:
            raise ValueError("REDIS_REQUIRED must be true in production")
        return self

    @property
    def trusted_host_list(self) -> list[str]:
        return [value.strip() for value in self.trusted_hosts.split(",") if value.strip()]

    @property
    def web_origin_list(self) -> list[str]:
        return [value.strip().rstrip("/") for value in self.web_origin.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""

    return Settings()
