from functools import lru_cache
from typing import Literal, Self

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables (.env)."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: str = "development"
    debug: bool = True
    backend_cors_origins: str = '["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:4200", "http://127.0.0.1:4200"]'
    frontend_url: str = "http://localhost:3000"

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
    google_client_id: str = (
        "408847171120-dldrof0cc90f3nn19qsl7amrl7fpc9jc.apps.googleusercontent.com"
    )

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

    # Provider-Agnostic LLM (ADR-006: gemini | openai | anthropic | ollama)
    llm_provider: str = "gemini"
    llm_thinking_control: Literal["model_suffix", "param"] = "model_suffix"
    llm_model: str = "gemini-3.8-flash-medium"
    llm_model_low: str = "gemini-3.8-flash-low"
    llm_model_medium: str = "gemini-3.8-flash-medium"
    llm_model_high: str = "gemini-3.8-flash-high"
    llm_embedding_model: str = "gemini/gemini-embedding-2"
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("llm_api_key", "llm_key"),
    )
    llm_base_url: str = ""
    llm_fallback_models: str = ""
    llm_thinking_level: str = "MEDIUM"
    llm_schema_enforced_by_gateway: bool = False
    llm_max_tool_calls: int = 4
    llm_tool_timeout_seconds: float = 5.0

    # Dedicated Google AI Studio Embedding (isolated from cobhub LLM gateway)
    embedding_provider: str = "google_ai_studio"
    embedding_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("embedding_api_key"),
    )
    embedding_model: str = "gemini/gemini-embedding-2"
    embedding_base_url: str = ""
    embedding_dimensions: int = 768

    # AI Hard Timeout & Stage Budgets (SRS v1.3 hard cap 55s; measured p95 * 1.3..1.5)
    ai_hard_timeout_seconds: float = 55.0
    ai_sse_pipeline_timeout_seconds: float = 55.0
    ai_clarifier_timeout_seconds: float = 15.0
    ai_clarifier_followup_timeout_seconds: float = 7.5
    ai_milestone_planner_timeout_seconds: float = 50.0
    ai_task_decomposer_timeout_seconds: float = 25.0
    ai_tool_call_timeout_seconds: float = 40.0
    ai_quality_critic_timeout_seconds: float = 15.0
    ai_quality_arbiter_timeout_seconds: float = 14.5
    tier3_judge_timeout_seconds: float = 8.0
    ai_weekly_review_timeout_seconds: float = 10.5
    ai_prove_question_timeout_seconds: float = 8.5
    ai_prove_grader_timeout_seconds: float = 7.5
    ai_min_critic_remaining_seconds: float = 6.0
    ai_min_judge_remaining_seconds: float = 3.0
    ai_min_retry_remaining_seconds: float = 12.0

    enable_tier3_judge: bool = True
    ai_harness_v2_enabled: bool = False
    clarification_engine_v2_enabled: bool = True
    knowledge_rag_enabled: bool = True
    learner_memory_enabled: bool = True
    ai_circuit_failure_threshold: int = 3
    ai_circuit_window_seconds: int = 60
    ai_circuit_open_seconds: int = 60
    knowledge_upload_dir: str = "/tmp/focusflow-knowledge"
    knowledge_file_max_bytes: int = 20 * 1024 * 1024
    knowledge_url_max_bytes: int = 5 * 1024 * 1024
    knowledge_url_timeout_seconds: float = 8.0

    # External Providers
    payment_provider: str = "sepay"
    calendar_provider: str = "google"
    calendar_encryption_key: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/api/v1/account/calendar/google/callback"
    calendar_webhook_base_url: str = "http://localhost:3000"

    @model_validator(mode="after")
    def _validate_ai_timeout_budgets(self) -> Self:
        if int(self.embedding_dimensions) <= 0:
            raise ValueError("embedding_dimensions must be > 0")
        hard_cap = float(self.ai_hard_timeout_seconds)
        if hard_cap <= 0:
            raise ValueError("ai_hard_timeout_seconds must be > 0")

        stage_fields = (
            "ai_sse_pipeline_timeout_seconds",
            "ai_clarifier_timeout_seconds",
            "ai_clarifier_followup_timeout_seconds",
            "ai_milestone_planner_timeout_seconds",
            "ai_task_decomposer_timeout_seconds",
            "ai_tool_call_timeout_seconds",
            "ai_quality_critic_timeout_seconds",
            "ai_quality_arbiter_timeout_seconds",
            "tier3_judge_timeout_seconds",
            "ai_weekly_review_timeout_seconds",
            "ai_prove_question_timeout_seconds",
            "ai_prove_grader_timeout_seconds",
            "ai_min_critic_remaining_seconds",
            "ai_min_judge_remaining_seconds",
            "ai_min_retry_remaining_seconds",
        )
        for field_name in stage_fields:
            val = float(getattr(self, field_name))
            if val <= 0:
                raise ValueError(f"{field_name} must be > 0 (got {val})")
            if val > hard_cap:
                raise ValueError(
                    f"{field_name} ({val}s) cannot exceed ai_hard_timeout_seconds ({hard_cap}s)"
                )

        if self.ai_tool_call_timeout_seconds > self.ai_milestone_planner_timeout_seconds:
            raise ValueError(
                "ai_tool_call_timeout_seconds cannot exceed ai_milestone_planner_timeout_seconds"
            )
        if self.ai_tool_call_timeout_seconds > self.ai_sse_pipeline_timeout_seconds:
            raise ValueError(
                "ai_tool_call_timeout_seconds cannot exceed ai_sse_pipeline_timeout_seconds"
            )
        if self.ai_milestone_planner_timeout_seconds > self.ai_sse_pipeline_timeout_seconds:
            raise ValueError(
                "ai_milestone_planner_timeout_seconds cannot exceed ai_sse_pipeline_timeout_seconds"
            )
        if self.ai_task_decomposer_timeout_seconds > self.ai_sse_pipeline_timeout_seconds:
            raise ValueError(
                "ai_task_decomposer_timeout_seconds cannot exceed ai_sse_pipeline_timeout_seconds"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
