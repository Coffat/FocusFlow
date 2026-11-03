from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables (.env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: str = "development"
    debug: bool = True
    backend_cors_origins: str = '["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:4200", "http://127.0.0.1:4200"]'

    # PostgreSQL 16 (Asyncpg)
    database_url: str = (
        "postgresql+asyncpg://focusflow_user:focusflow_secure_password@localhost:5432/focusflow_db"
    )
    database_url_sync: str = (
        "postgresql://focusflow_user:focusflow_secure_password@localhost:5432/focusflow_db"
    )

    # Redis 7 (AOF + Streams)
    redis_url: str = "redis://localhost:6379/0"

    # Security & Auth (Argon2id + PyJWT + Fernet)
    secret_key: str = "change_this_to_a_super_secret_64_character_hex_key_for_jwt_signing"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    fernet_key: str = ""
    google_client_id: str = ""

    # Mail & OTP Configuration (ADR-008, Mailpit on localhost:1025 in dev/test)
    email_backend: str = "smtp"
    email_host: str = "localhost"
    email_port: int = 1025
    email_user: str = ""
    email_pass: str = ""
    email_from: str = "FocusFlow Support <no-reply@focusflow.local>"
    otp_ttl_seconds: int = 300
    otp_cooldown_seconds: int = 60
    otp_max_attempts: int = 3

    # Provider-Agnostic LLM (ADR-006: gemini | openai | anthropic | ollama | mock)
    llm_provider: str = "gemini"
    llm_model: str = "gemini-3.8-flash"
    llm_api_key: str = Field(
        default="mock-key",
        validation_alias=AliasChoices("llm_api_key", "gemini_api_key", "llm_key"),
    )
    llm_base_url: str = ""
    llm_thinking_level: str = "MEDIUM"
    llm_max_tool_calls: int = 4
    llm_tool_timeout_seconds: float = 5.0
    enable_tier3_judge: bool = True

    # External Providers (Sandbox / Mock fallback for offline thesis defense)
    payment_provider: str = "mock"
    calendar_provider: str = "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
