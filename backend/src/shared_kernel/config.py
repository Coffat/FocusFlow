import logging
from functools import lru_cache
from typing import Any, Literal, Self

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_logger = logging.getLogger(__name__)

_DEFAULT_SECRET_KEY = "change_this_to_a_super_secret_64_character_hex_key_for_jwt_signing"


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
    secret_key: str = _DEFAULT_SECRET_KEY
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
    ai_task_decomposer_timeout_seconds: float = 36.0
    ai_tool_call_timeout_seconds: float = 40.0
    ai_quality_critic_timeout_seconds: float = 15.0
    ai_quality_arbiter_timeout_seconds: float = 14.5
    tier3_judge_timeout_seconds: float = 12.0
    ai_weekly_review_timeout_seconds: float = 10.5
    ai_prove_question_timeout_seconds: float = 8.5
    ai_prove_grader_timeout_seconds: float = 7.5
    ai_min_critic_remaining_seconds: float = 6.0
    ai_min_judge_remaining_seconds: float = 3.0
    ai_min_retry_remaining_seconds: float = 12.0

    enable_tier3_judge: bool = True
    decomposer_architecture_mode: Literal["monolithic", "milestone_scoped"] = "milestone_scoped"
    ai_max_concurrent_llm_requests: int = 4
    ai_decomposer_max_concurrency: int = 2
    ai_harness_v2_enabled: bool = False
    clarification_engine_v2_enabled: bool = True
    knowledge_rag_enabled: bool = True
    learner_memory_enabled: bool = True
    spatio_temporal_v2_hard_solver_enabled: bool = True
    spatio_temporal_v2_soft_pacing_enabled: bool = True
    spatio_temporal_soft_end_buffer_ratio: float = 0.12
    spatio_temporal_soft_max_consecutive_days: int = 5
    milestone_effort_allocator_enabled: bool = True
    ai_milestone_target_utilization: float = 0.85
    ai_milestone_min_effort_ratio: float = 0.65
    ai_milestone_alpha_beginner: float = 1.15
    ai_milestone_alpha_intermediate: float = 1.00
    ai_milestone_alpha_advanced: float = 0.85
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
        if not (0.0 < float(self.ai_milestone_target_utilization) <= 1.0):
            raise ValueError("ai_milestone_target_utilization must be in (0.0, 1.0]")
        if not (0.0 < float(self.ai_milestone_min_effort_ratio) <= 1.0):
            raise ValueError("ai_milestone_min_effort_ratio must be in (0.0, 1.0]")
        if not (0.0 <= float(self.spatio_temporal_soft_end_buffer_ratio) < 1.0):
            raise ValueError("spatio_temporal_soft_end_buffer_ratio must be in [0.0, 1.0)")
        if int(self.spatio_temporal_soft_max_consecutive_days) < 1:
            raise ValueError("spatio_temporal_soft_max_consecutive_days must be >= 1")
        if int(self.embedding_dimensions) <= 0:
            raise ValueError("embedding_dimensions must be > 0")
        if int(self.ai_max_concurrent_llm_requests) < 1:
            raise ValueError("ai_max_concurrent_llm_requests must be >= 1")
        if int(self.ai_decomposer_max_concurrency) < 1:
            raise ValueError("ai_decomposer_max_concurrency must be >= 1")
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

    @model_validator(mode="after")
    def _validate_environment_security(self) -> Self:
        env = (self.environment or "").strip().lower()
        if env in ("staging", "production") and self.debug:
            raise ValueError("debug must be False in staging/production")
        using_default_secret = not self.secret_key.strip() or self.secret_key == _DEFAULT_SECRET_KEY
        if env == "production" and using_default_secret:
            raise ValueError("secret_key must not use the default value in production")
        if env == "staging" and using_default_secret:
            _logger.warning(
                "Staging environment is using the default secret_key; override SECRET_KEY before public exposure."
            )
        return self

    def staging_readiness_summary(self) -> dict[str, Any]:
        """Return strictly non-secret readiness flags for health/staging diagnostics."""
        return {
            "environment": self.environment,
            "debug": self.debug,
            "rag_embedding_configured": bool((self.embedding_api_key or "").strip()),
            "email_backend": self.email_backend,
            "email_host": self.email_host,
            "calendar_webhook_https_ready": (
                (self.calendar_webhook_base_url or "").strip().lower().startswith("https://")
            ),
            "secret_key_is_default": self.secret_key == _DEFAULT_SECRET_KEY,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
