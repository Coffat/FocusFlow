import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "FocusFlow"
    VERSION: str = "1.0.0"

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str = "focusflow_user"
    POSTGRES_PASSWORD: str = "focusflow_secure_password"
    POSTGRES_DB: str = "focusflow_db"
    DATABASE_URL: str = "postgresql+asyncpg://focusflow_user:focusflow_secure_password@localhost:5433/focusflow_db"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security & JWT (ADR-008)
    SECRET_KEY: str = "dev_insecure_secret_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GOOGLE_CLIENT_ID: str = ""

    # Mail & OTP Configuration
    EMAIL_BACKEND: str = "console"
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USER: str = ""
    EMAIL_PASS: str = ""
    EMAIL_FROM: str = "FocusFlow Support <no-reply@focusflow.local>"
    OTP_TTL_SECONDS: int = 180
    OTP_COOLDOWN_SECONDS: int = 60
    OTP_MAX_ATTEMPTS: int = 3

    # CORS
    BACKEND_CORS_ORIGINS: list[str] | str = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        return v


settings = Settings()
