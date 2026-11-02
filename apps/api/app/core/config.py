"""Typed application settings.

All configuration comes from environment variables (or a local ``.env`` file in development).
The process fails fast on missing or invalid values — there are no hidden defaults for anything
that differs between environments (MEP §59, §70).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import (
    EmailStr,
    Field,
    HttpUrl,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

AppEnv = Literal["development", "test", "staging", "production"]
LogFormat = Literal["console", "json"]

# Shortest secret we accept for keyed hashing / HMAC inputs (security.md §1).
MIN_SECRET_LENGTH = 32

#: Rate limits are configured as ``"<events>/<window seconds>"``, parsed by
#: :meth:`app.core.rate_limit.RateLimit.parse`.
RATE_LIMIT_SPEC_PATTERN = r"^[1-9]\d{0,5}/[1-9]\d{0,6}$"


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
    # ~2000 concurrent riders/drivers share this pool across API replicas.
    database_pool_size: int = Field(default=20, ge=1, le=100, alias="DATABASE_POOL_SIZE")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")

    redis_url: RedisDsn = Field(alias="REDIS_URL")

    # NoDecode: the value is a comma-separated string, not JSON; parsed by the validator below.
    cors_origins: Annotated[list[HttpUrl], NoDecode] = Field(
        default_factory=list, alias="CORS_ORIGINS"
    )
    public_web_url: HttpUrl = Field(alias="PUBLIC_WEB_URL")

    # --- Authentication (ADR-0004, security.md §1) ---------------------------------------
    # Ed25519 signing key for access tokens: base64 (standard or url-safe) of the 32-byte seed.
    # Generate with ``python -m scripts.generate_auth_keys`` (see docs/runbooks).
    auth_jwt_active_kid: str = Field(alias="AUTH_JWT_ACTIVE_KID", min_length=1, max_length=32)
    auth_jwt_private_key: SecretStr = Field(alias="AUTH_JWT_PRIVATE_KEY")
    # Public keys of retired key ids, kept so tokens signed before a rotation still verify.
    # Format: ``kid1:base64pub,kid2:base64pub``.
    auth_jwt_retired_public_keys: Annotated[dict[str, str], NoDecode] = Field(
        default_factory=dict, alias="AUTH_JWT_RETIRED_PUBLIC_KEYS"
    )
    auth_access_token_ttl_seconds: int = Field(
        default=900, ge=60, le=3600, alias="AUTH_ACCESS_TOKEN_TTL_SECONDS"
    )
    auth_refresh_token_ttl_days: int = Field(
        default=30, ge=1, le=365, alias="AUTH_REFRESH_TOKEN_TTL_DAYS"
    )
    auth_refresh_absolute_ttl_days: int = Field(
        default=90, ge=1, le=730, alias="AUTH_REFRESH_ABSOLUTE_TTL_DAYS"
    )
    auth_password_min_length: int = Field(default=10, ge=8, le=64, alias="AUTH_PASSWORD_MIN_LENGTH")
    auth_password_pepper: SecretStr = Field(alias="AUTH_PASSWORD_PEPPER")
    auth_csrf_secret: SecretStr = Field(alias="AUTH_CSRF_SECRET")
    # Keyed hash for IP addresses and identifiers in rate-limit keys and audit rows: the raw
    # values are never stored (security.md §9, §10).
    auth_hash_secret: SecretStr = Field(alias="AUTH_HASH_SECRET")
    auth_email_verification_ttl_hours: int = Field(
        default=24, ge=1, le=168, alias="AUTH_EMAIL_VERIFICATION_TTL_HOURS"
    )
    auth_password_reset_ttl_minutes: int = Field(
        default=60, ge=5, le=1440, alias="AUTH_PASSWORD_RESET_TTL_MINUTES"
    )

    # Rate limits as ``"<events>/<window seconds>"`` (security.md §7). Defaults are the
    # documented values; they are configuration so a limit can be tightened without a release.
    auth_login_rate_limit_per_ip: str = Field(
        default="10/900", alias="AUTH_LOGIN_RATE_LIMIT_PER_IP", pattern=RATE_LIMIT_SPEC_PATTERN
    )
    auth_login_rate_limit_per_identifier: str = Field(
        default="5/900",
        alias="AUTH_LOGIN_RATE_LIMIT_PER_IDENTIFIER",
        pattern=RATE_LIMIT_SPEC_PATTERN,
    )
    auth_register_rate_limit: str = Field(
        default="5/3600", alias="AUTH_REGISTER_RATE_LIMIT", pattern=RATE_LIMIT_SPEC_PATTERN
    )
    auth_forgot_rate_limit_per_identifier: str = Field(
        default="3/3600",
        alias="AUTH_FORGOT_RATE_LIMIT_PER_IDENTIFIER",
        pattern=RATE_LIMIT_SPEC_PATTERN,
    )
    auth_forgot_rate_limit_per_ip: str = Field(
        default="10/3600", alias="AUTH_FORGOT_RATE_LIMIT_PER_IP", pattern=RATE_LIMIT_SPEC_PATTERN
    )
    auth_email_resend_rate_limit: str = Field(
        default="3/3600", alias="AUTH_EMAIL_RESEND_RATE_LIMIT", pattern=RATE_LIMIT_SPEC_PATTERN
    )

    argon2_time_cost: int = Field(default=3, ge=1, le=10, alias="ARGON2_TIME_COST")
    argon2_memory_cost_kib: int = Field(
        default=65536, ge=8192, le=1048576, alias="ARGON2_MEMORY_COST_KIB"
    )
    argon2_parallelism: int = Field(default=4, ge=1, le=16, alias="ARGON2_PARALLELISM")

    # --- Accounts & legal (BR-ACC-07, BR-ACC-08) -----------------------------------------
    accounts_deletion_grace_days: int = Field(
        default=14, ge=0, le=90, alias="ACCOUNTS_DELETION_GRACE_DAYS"
    )
    accounts_minimum_age_years: int = Field(
        default=18, ge=13, le=25, alias="ACCOUNTS_MINIMUM_AGE_YEARS"
    )
    legal_terms_version: str = Field(default="2026-10-01", alias="LEGAL_TERMS_VERSION")
    legal_privacy_version: str = Field(default="2026-10-01", alias="LEGAL_PRIVACY_VERSION")

    # --- Outbound email (OD-019: SMTP behind an EmailSender port) -------------------------
    email_from_address: EmailStr = Field(alias="EMAIL_FROM_ADDRESS")
    email_from_name: str = Field(default="Fi Sikkati", alias="EMAIL_FROM_NAME")
    smtp_host: str = Field(alias="SMTP_HOST")
    smtp_port: int = Field(default=1025, ge=1, le=65535, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: SecretStr | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=False, alias="SMTP_USE_TLS")
    smtp_use_starttls: bool = Field(default=False, alias="SMTP_USE_STARTTLS")

    # Phone alerts (Web Push). Required in production so a trip or chat alert
    # still reaches the device after the site is closed.
    vapid_public_key: str = Field(default="", alias="VAPID_PUBLIC_KEY")
    vapid_private_key: SecretStr = Field(default=SecretStr(""), alias="VAPID_PRIVATE_KEY")
    vapid_subject: str = Field(default="mailto:no-reply@fisikkati.app", alias="VAPID_SUBJECT")
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: SecretStr = Field(default=SecretStr(""), alias="TWILIO_AUTH_TOKEN")
    sms_from: str = Field(default="", alias="SMS_FROM")
    phone_otp_ttl_minutes: int = Field(default=10, alias="PHONE_OTP_TTL_MINUTES")

    # --- Object storage (ADR-0013). Local defaults match infra/compose MinIO. --------------
    s3_endpoint: str = Field(default="http://127.0.0.1:9100", alias="S3_ENDPOINT")
    s3_access_key: str = Field(default="minio_dev", alias="S3_ACCESS_KEY")
    s3_secret_key: SecretStr = Field(default=SecretStr("minio_dev_password"), alias="S3_SECRET_KEY")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_public_bucket: str = Field(default="public-media", alias="S3_PUBLIC_BUCKET")
    s3_private_bucket: str = Field(default="private-documents", alias="S3_PRIVATE_BUCKET")
    s3_use_ssl: bool = Field(default=False, alias="S3_USE_SSL")
    s3_public_base_url: str = Field(
        default="http://127.0.0.1:9100/public-media", alias="S3_PUBLIC_BASE_URL"
    )

    # --- Verification & vehicles (OD-003/009/022/024 approved 2026-10-02) -----------------
    verification_document_retention_days: int = Field(
        default=30, ge=1, le=365, alias="VERIFICATION_DOCUMENT_RETENTION_DAYS"
    )
    verification_review_sla_hours: int = Field(
        default=48, ge=1, le=720, alias="VERIFICATION_REVIEW_SLA_HOURS"
    )
    verification_licence_expiry_notice_days: int = Field(
        default=30, ge=1, le=365, alias="VERIFICATION_LICENCE_EXPIRY_NOTICE_DAYS"
    )
    verification_identity_required_before_join: bool = Field(
        default=True, alias="VERIFICATION_IDENTITY_REQUIRED_BEFORE_JOIN"
    )
    vehicles_max_per_driver: int = Field(default=3, ge=1, le=10, alias="VEHICLES_MAX_PER_DRIVER")
    uploads_max_document_bytes: int = Field(
        default=10 * 1024 * 1024,
        ge=1024,
        le=50 * 1024 * 1024,
        alias="UPLOADS_MAX_DOCUMENT_BYTES",
    )
    uploads_signed_url_ttl_seconds: int = Field(
        default=120, ge=30, le=600, alias="UPLOADS_SIGNED_URL_TTL_SECONDS"
    )

    # --- Maps, trips, pricing (OD-001/005/006/007/012/017/023 approved 2026-10-02) ---------
    mapbox_access_token: SecretStr | None = Field(default=None, alias="MAPBOX_ACCESS_TOKEN")
    mapbox_public_token: str | None = Field(default=None, alias="MAPBOX_PUBLIC_TOKEN")
    trips_max_passenger_seats: int = Field(
        default=7, ge=1, le=20, alias="TRIPS_MAX_PASSENGER_SEATS"
    )
    trips_expire_grace_minutes: int = Field(
        default=60, ge=1, le=1440, alias="TRIPS_EXPIRE_GRACE_MINUTES"
    )
    trips_start_window_minutes: int = Field(
        default=30, ge=0, le=240, alias="TRIPS_START_WINDOW_MINUTES"
    )
    trips_auto_complete_hours: int = Field(
        default=6, ge=1, le=48, alias="TRIPS_AUTO_COMPLETE_HOURS"
    )
    trips_edit_departure_tolerance_minutes: int = Field(
        default=15, ge=0, le=180, alias="TRIPS_EDIT_DEPARTURE_TOLERANCE_MINUTES"
    )
    # Finished trips (and their trip chat) older than today's Cairo midnight are removed daily.
    trips_daily_purge_enabled: bool = Field(default=True, alias="TRIPS_DAILY_PURGE_ENABLED")
    matching_corridor_width_meters: int = Field(
        default=1000, ge=100, le=5000, alias="MATCHING_CORRIDOR_WIDTH_METERS"
    )
    matching_stop_proximity_meters: int = Field(
        default=500, ge=50, le=2000, alias="MATCHING_STOP_PROXIMITY_METERS"
    )
    matching_default_time_window_minutes: int = Field(
        default=60, ge=15, le=240, alias="MATCHING_DEFAULT_TIME_WINDOW_MINUTES"
    )
    search_trips_rate_limit: str = Field(
        default="60/60",
        pattern=RATE_LIMIT_SPEC_PATTERN,
        alias="SEARCH_TRIPS_RATE_LIMIT",
    )
    privacy_location_blur_meters: int = Field(
        default=500, ge=50, le=5000, alias="PRIVACY_LOCATION_BLUR_METERS"
    )

    # --- Bookings (OD-008/014 approved 2026-10-15) -----------------------------------------
    bookings_max_seats_per_request: int = Field(
        default=7, ge=1, le=20, alias="BOOKINGS_MAX_SEATS_PER_REQUEST"
    )
    bookings_cancellation_window_days: int = Field(
        default=90, ge=1, le=365, alias="BOOKINGS_CANCELLATION_WINDOW_DAYS"
    )
    bookings_late_cancel_minutes: int = Field(
        default=120, ge=0, le=1440, alias="BOOKINGS_LATE_CANCEL_MINUTES"
    )

    # --- Chat & notifications (Phase 7; OD-011/015 approved 2026-10-19) -------------------
    chat_message_max_length: int = Field(
        default=2000, ge=100, le=10000, alias="CHAT_MESSAGE_MAX_LENGTH"
    )
    chat_rate_limit_per_user: str = Field(
        default="30/60", pattern=RATE_LIMIT_SPEC_PATTERN, alias="CHAT_RATE_LIMIT_PER_USER"
    )
    chat_post_completion_open_hours: int = Field(
        default=24, ge=0, le=168, alias="CHAT_POST_COMPLETION_OPEN_HOURS"
    )
    chat_poll_interval_seconds: int = Field(
        default=5, ge=2, le=60, alias="CHAT_POLL_INTERVAL_SECONDS"
    )
    notifications_trip_reminder_hours: int = Field(
        default=24, ge=1, le=72, alias="NOTIFICATIONS_TRIP_REMINDER_HOURS"
    )
    notifications_starting_soon_minutes: int = Field(
        default=120, ge=15, le=720, alias="NOTIFICATIONS_STARTING_SOON_MINUTES"
    )
    notifications_email_batch_size: int = Field(
        default=100, ge=1, le=1000, alias="NOTIFICATIONS_EMAIL_BATCH_SIZE"
    )

    # --- Safety & trust (Phase 8; OD-010/016/020 approved 2026-10-19) ---------------------
    ratings_window_days: int = Field(default=14, ge=1, le=90, alias="RATINGS_WINDOW_DAYS")
    ratings_min_count_to_display: int = Field(
        default=3, ge=1, le=20, alias="RATINGS_MIN_COUNT_TO_DISPLAY"
    )
    reports_per_user_per_day: str = Field(
        default="10/86400", pattern=RATE_LIMIT_SPEC_PATTERN, alias="REPORTS_PER_USER_PER_DAY"
    )
    reports_auto_hide_threshold: int = Field(
        default=3, ge=1, le=20, alias="REPORTS_AUTO_HIDE_THRESHOLD"
    )

    # --- AI assistant (Phase 10; OD-025 approved 2026-10-19) ------------------------------
    ai_enabled: bool = Field(default=False, alias="AI_ENABLED")
    ai_provider: Literal["rules", "openai_compatible"] = Field(default="rules", alias="AI_PROVIDER")
    ai_provider_base_url: HttpUrl | None = Field(default=None, alias="AI_PROVIDER_BASE_URL")
    ai_provider_api_key: SecretStr | None = Field(default=None, alias="AI_PROVIDER_API_KEY")
    ai_provider_model: str = Field(default="gpt-4o-mini", alias="AI_PROVIDER_MODEL")
    ai_rate_limit_per_user: str = Field(
        default="30/3600", pattern=RATE_LIMIT_SPEC_PATTERN, alias="AI_RATE_LIMIT_PER_USER"
    )
    ai_timeout_seconds: float = Field(default=12.0, ge=1, le=60, alias="AI_TIMEOUT_SECONDS")

    # --- Admin platform (Phase 9) ----------------------------------------------------------
    admin_rate_limit_per_user: str = Field(
        default="600/60", pattern=RATE_LIMIT_SPEC_PATTERN, alias="ADMIN_RATE_LIMIT_PER_USER"
    )

    @field_validator("auth_jwt_retired_public_keys", mode="before")
    @classmethod
    def _parse_retired_keys(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        keys: dict[str, str] = {}
        for entry in value.split(","):
            item = entry.strip()
            if not item:
                continue
            kid, separator, public_key = item.partition(":")
            if not separator or not kid.strip() or not public_key.strip():
                msg = "AUTH_JWT_RETIRED_PUBLIC_KEYS must be a list of 'kid:base64key' pairs"
                raise ValueError(msg)
            keys[kid.strip()] = public_key.strip()
        return keys

    @field_validator("auth_password_pepper", "auth_csrf_secret", "auth_hash_secret", mode="after")
    @classmethod
    def _require_strong_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < MIN_SECRET_LENGTH:
            msg = f"secrets must be at least {MIN_SECRET_LENGTH} characters long"
            raise ValueError(msg)
        return value

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

    @model_validator(mode="after")
    def _check_token_lifetimes(self) -> Settings:
        if self.auth_refresh_absolute_ttl_days < self.auth_refresh_token_ttl_days:
            msg = "AUTH_REFRESH_ABSOLUTE_TTL_DAYS must not be below AUTH_REFRESH_TOKEN_TTL_DAYS"
            raise ValueError(msg)
        if self.app_env == "production" and (
            not self.vapid_public_key or not self.vapid_private_key.get_secret_value()
        ):
            msg = "VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY are required in production"
            raise ValueError(msg)
        if self.app_env == "production" and not self.sms_configured:
            msg = "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and SMS_FROM are required in production"
            raise ValueError(msg)
        return self

    @property
    def sms_configured(self) -> bool:
        return bool(
            self.twilio_account_sid and self.twilio_auth_token.get_secret_value() and self.sms_from
        )

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
