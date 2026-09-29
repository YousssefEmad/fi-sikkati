"""Typed application settings.

All configuration comes from environment variables (or a local ``.env`` file in development).
The process fails fast on missing or invalid values — there are no hidden defaults for anything
that differs between environments (MEP §59, §70).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

AppEnv = Literal["development", "test", "staging", "production"]
LogFormat = Literal["console", "json"]


class Settings(BaseSettings):
    """Runtime configuration for the API and worker processes."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    app_env: AppEnv = Field(alias="APP_ENV")
    app_name: str = Field(default="fi-sikkati-api", alias="APP_NAME")
    api_version: str = Field(default="v1", alias="API_VERSION")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )
    log_format: LogFormat = Field(default="json", alias="LOG_FORMAT")

    database_url: PostgresDsn = Field(alias="DATABASE_URL")
    migration_database_url: PostgresDsn | None = Field(default=None, alias="MIGRATION_DATABASE_URL")
    database_pool_size: int = Field(default=10, ge=1, le=100, alias="DATABASE_POOL_SIZE")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")

    redis_url: RedisDsn = Field(alias="REDIS_URL")

    # NoDecode: the value is a comma-separated string, not JSON; parsed by the validator below.
    cors_origins: Annotated[list[HttpUrl], NoDecode] = Field(
        default_factory=list, alias="CORS_ORIGINS"
    )
    public_web_url: HttpUrl = Field(alias="PUBLIC_WEB_URL")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("database_url", "migration_database_url", mode="after")
    @classmethod
    def _require_asyncpg_driver(cls, value: PostgresDsn | None) -> PostgresDsn | None:
        if value is not None and value.scheme != "postgresql+asyncpg":
            msg = "database URLs must use the 'postgresql+asyncpg' scheme"
            raise ValueError(msg)
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def docs_enabled(self) -> bool:
        """Interactive API docs are exposed only outside production (api.md §6)."""
        return self.app_env in {"development", "test", "staging"}

    @property
    def cors_origin_strings(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.cors_origins]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance (cached; tests clear the cache)."""
    return Settings()  # populated from environment by pydantic-settings
