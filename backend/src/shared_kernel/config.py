import base64
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Self
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_logger = logging.getLogger(__name__)

_DEFAULT_SECRET_KEY = "change_this_to_a_super_secret_64_character_hex_key_for_jwt_signing"


def _is_valid_fernet_key(key: str) -> bool:
    """Return True iff key is a valid 32-byte url-safe base64 Fernet key."""
    cleaned = (key or "").strip()
    if not cleaned:
        return False
    try:
        raw_key = cleaned.encode("utf-8")
        decoded = base64.urlsafe_b64decode(raw_key)
        if len(decoded) != 32:
            return False
        Fernet(raw_key)
        return True
    except Exception:
        return False


_DEFAULT_CORS_ORIGINS: tuple[str, ...] = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4200",
    "http://127.0.0.1:4200",
)


def normalize_origin(raw: str, *, allow_url_path: bool = False) -> str | None:
    """Normalize an HTTP(S) origin string to ``scheme://host[:port]``.

    Returns ``None`` for wildcards, ``null``, non-HTTP(S) schemes, credentials,
    malformed URLs, or (when ``allow_url_path=False``) values containing a path,
    query, or fragment.
    """
    cleaned = (raw or "").strip()
    if not cleaned or cleaned == "*" or cleaned.lower() == "null":
        return None
    if any(ch.isspace() for ch in cleaned):
        return None

    try:
        parsed = urlsplit(cleaned)
    except ValueError:
        return None

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    if not allow_url_path and (parsed.path or parsed.query or parsed.fragment):
        return None

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return None

    try:
        port = parsed.port
    except ValueError:
        return None

    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None

    host_part = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        return f"{scheme}://{host_part}:{port}"
    return f"{scheme}://{host_part}"


def _parse_origin_list(raw: str) -> list[str]:
    """Parse a JSON array or comma-separated origin string into raw entries."""
    cleaned = (raw or "").strip()
    if not cleaned:
        return []
    if cleaned.startswith("["):
        parsed = json.loads(cleaned)
        if not isinstance(parsed, list):
            raise ValueError("Origin configuration JSON must be a list of origin strings")
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [part.strip() for part in cleaned.split(",") if part.strip()]


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
    csrf_trusted_origins: str = ""
    frontend_url: str = "http://localhost:3000"

    # PostgreSQL 16 (Asyncpg)
    database_url: str = (
        "postgresql+asyncpg://focusflow_user:focusflow_secure_password@localhost:5432/focusflow_db"
    )
    database_url_sync: str = (
        "postgresql://focusflow_user:focusflow_secure_password@localhost:5432/focusflow_db"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 10
    db_pool_timeout: float = 15.0
    db_pool_recycle: int = 1800
    db_pool_pre_ping: bool = True
    db_connect_timeout: float = 10.0
    db_command_timeout: float = 23.0
    db_statement_timeout_ms: int = 20000
    db_lock_timeout_ms: int = 10000

    # Redis 7 (AOF + Streams)
    redis_url: str = "redis://localhost:6379/0"

    # Distributed Rate Limiting (AUD-HIGH-05)
    rate_limit_enabled: bool = True
    rate_limit_trusted_proxies: str = "127.0.0.1/32,::1/128,172.16.0.0/12,10.0.0.0/8,192.168.0.0/16"
    rate_limit_overrides_json: str = ""

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
    ai_prove_question_timeout_seconds: float = 20.0
    ai_prove_grader_timeout_seconds: float = 25.0
    ai_min_critic_remaining_seconds: float = 6.0
    ai_min_judge_remaining_seconds: float = 3.0
    ai_min_retry_remaining_seconds: float = 12.0
    ai_proposal_finalize_reserve_seconds: float = 6.0

    enable_tier3_judge: bool = True
    decomposer_architecture_mode: Literal["monolithic", "milestone_scoped"] = "milestone_scoped"
    ai_max_concurrent_llm_requests: int = 4
    ai_decomposer_max_concurrency: int = 4
    ai_harness_v2_enabled: bool = True
    ai_circuit_breaker_enabled: bool = True
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
    knowledge_upload_dir: str = Field(
        default_factory=lambda: str(
            Path(tempfile.gettempdir())
            / f"focusflow-knowledge-{os.getuid() if hasattr(os, 'getuid') else 'private'}"
        )
    )
    knowledge_file_max_bytes: int = 20 * 1024 * 1024
    knowledge_url_max_bytes: int = 5 * 1024 * 1024
    knowledge_url_timeout_seconds: float = 8.0
    knowledge_max_extracted_chars: int = 500_000
    knowledge_docx_max_entries: int = 500
    knowledge_docx_max_uncompressed_bytes: int = 50 * 1024 * 1024
    knowledge_docx_max_compression_ratio: float = 100.0
    knowledge_pdf_max_pages: int = 500

    # External Providers & Billing Release Gating
    billing_release_mode: Literal["FREE_BETA", "PAID_ENABLED"] = "FREE_BETA"
    payment_provider: str = "sepay"
    payment_webhook_secret: str = ""
    calendar_provider: str = "google"
    calendar_encryption_key: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/api/v1/account/calendar/google/callback"
    calendar_webhook_base_url: str = "http://localhost:3000"

    @model_validator(mode="after")
    def _validate_db_pool_settings(self) -> Self:
        if int(self.db_pool_size) < 1:
            raise ValueError("db_pool_size must be >= 1")
        if int(self.db_max_overflow) < 0:
            raise ValueError("db_max_overflow must be >= 0")
        if float(self.db_pool_timeout) <= 0:
            raise ValueError("db_pool_timeout must be > 0")
        if int(self.db_pool_recycle) < 0:
            raise ValueError("db_pool_recycle must be >= 0")
        if float(self.db_connect_timeout) <= 0:
            raise ValueError("db_connect_timeout must be > 0")
        if float(self.db_command_timeout) <= 0:
            raise ValueError("db_command_timeout must be > 0")
        if int(self.db_statement_timeout_ms) <= 0:
            raise ValueError("db_statement_timeout_ms must be > 0")
        if int(self.db_lock_timeout_ms) <= 0:
            raise ValueError("db_lock_timeout_ms must be > 0")
        return self

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
            "ai_proposal_finalize_reserve_seconds",
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
        if self.ai_proposal_finalize_reserve_seconds >= self.ai_sse_pipeline_timeout_seconds:
            raise ValueError(
                "ai_proposal_finalize_reserve_seconds must be smaller than "
                "ai_sse_pipeline_timeout_seconds"
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
        cal_provider = (self.calendar_provider or "").strip().lower()
        if cal_provider in ("google", "google_calendar"):
            effective_cal_key = (self.calendar_encryption_key or self.fernet_key).strip()
            if not _is_valid_fernet_key(effective_cal_key):
                if env == "production":
                    raise ValueError(
                        "CALENDAR_ENCRYPTION_KEY (or FERNET_KEY) must be a valid 32-byte "
                        "url-safe base64 Fernet key in production when calendar_provider='google'"
                    )
                if env == "staging":
                    _logger.warning(
                        "Staging environment has calendar_provider='google' without a valid "
                        "CALENDAR_ENCRYPTION_KEY; configure a valid Fernet key before public exposure."
                    )
        raw_cors_entries = _parse_origin_list(self.backend_cors_origins)
        if any(entry == "*" for entry in raw_cors_entries):
            raise ValueError(
                "backend_cors_origins must not contain '*' when credentialed CORS is enabled"
            )
        raw_csrf_entries = _parse_origin_list(self.csrf_trusted_origins)
        if any(entry == "*" for entry in raw_csrf_entries):
            raise ValueError("csrf_trusted_origins must not contain '*'")
        return self

    @property
    def cors_origins(self) -> list[str]:
        """Return normalized explicit CORS origins (never containing wildcard '*')."""
        raw_entries = _parse_origin_list(self.backend_cors_origins)
        if not raw_entries:
            raw_entries = list(_DEFAULT_CORS_ORIGINS)

        normalized: list[str] = []
        for entry in raw_entries:
            origin = normalize_origin(entry, allow_url_path=False)
            if origin and origin not in normalized:
                normalized.append(origin)
        return normalized

    @property
    def csrf_trusted_origin_set(self) -> frozenset[str]:
        """Return normalized origins trusted for cookie-authenticated CSRF checks."""
        trusted: set[str] = set(self.cors_origins)

        frontend_origin = normalize_origin(self.frontend_url, allow_url_path=True)
        if frontend_origin:
            trusted.add(frontend_origin)

        for entry in _parse_origin_list(self.csrf_trusted_origins):
            origin = normalize_origin(entry, allow_url_path=False)
            if origin:
                trusted.add(origin)

        return frozenset(trusted)

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


DEV_TEST_ENVIRONMENTS: frozenset[str] = frozenset({"development", "dev", "test", "local"})
IMPLEMENTED_LIVE_PAYMENT_PROVIDERS: frozenset[str] = frozenset()

FREE_BETA_STATUS_MESSAGE = "FocusFlow đang trong giai đoạn Free Beta — gói Premium sẽ sớm mở bán."
PAID_UNAVAILABLE_STATUS_MESSAGE = (
    "Cổng thanh toán trực tuyến chưa sẵn sàng trong môi trường hiện tại."
)
LOCAL_MOCK_STATUS_MESSAGE = (
    "Chế độ thanh toán giả lập (local_mock) đang bật cho môi trường thử nghiệm cô lập."
)


@dataclass(frozen=True, slots=True)
class BillingCapabilities:
    """Server-owned, fail-closed billing capability matrix derived from Settings."""

    release_mode: Literal["FREE_BETA", "PAID_ENABLED"]
    checkout_enabled: bool
    mock_confirm_enabled: bool
    provider: str
    status_message: str
    unavailable_code: str | None = None
    unavailable_reason: str | None = None


def resolve_billing_capabilities(settings: Settings) -> BillingCapabilities:
    """Resolve billing release mode and payment capabilities fail-closed.

    - FREE_BETA: Disables checkout and mock-confirm across all environments.
    - PAID_ENABLED:
      * In dev/test/local with PAYMENT_PROVIDER=local_mock: enables isolated mock checkout/confirm.
      * In staging/production: NEVER allows local_mock; requires an implemented live provider
        AND a non-empty PAYMENT_WEBHOOK_SECRET, otherwise fails closed.
    """
    release_mode = settings.billing_release_mode
    env = (settings.environment or "").strip().lower()
    provider = (settings.payment_provider or "").strip().lower()

    if release_mode == "FREE_BETA":
        return BillingCapabilities(
            release_mode="FREE_BETA",
            checkout_enabled=False,
            mock_confirm_enabled=False,
            provider="none",
            status_message=FREE_BETA_STATUS_MESSAGE,
            unavailable_code="BILLING_FREE_BETA_DISABLED",
            unavailable_reason=f"BILLING_FREE_BETA_DISABLED: {FREE_BETA_STATUS_MESSAGE}",
        )

    # MODE B: PAID_ENABLED
    if provider == "local_mock":
        if env in DEV_TEST_ENVIRONMENTS:
            return BillingCapabilities(
                release_mode="PAID_ENABLED",
                checkout_enabled=True,
                mock_confirm_enabled=True,
                provider="local_mock",
                status_message=LOCAL_MOCK_STATUS_MESSAGE,
            )
        return BillingCapabilities(
            release_mode="PAID_ENABLED",
            checkout_enabled=False,
            mock_confirm_enabled=False,
            provider="none",
            status_message=PAID_UNAVAILABLE_STATUS_MESSAGE,
            unavailable_code="BILLING_MOCK_FORBIDDEN",
            unavailable_reason=(
                f"Mock payment provider (local_mock) is disabled in '{env}' environment; "
                f"a live payment gateway adapter is not configured."
            ),
        )

    if provider in IMPLEMENTED_LIVE_PAYMENT_PROVIDERS:
        if not (settings.payment_webhook_secret or "").strip():
            return BillingCapabilities(
                release_mode="PAID_ENABLED",
                checkout_enabled=False,
                mock_confirm_enabled=False,
                provider="none",
                status_message="Cổng thanh toán trực tuyến chưa hoàn tất cấu hình bảo mật.",
                unavailable_code="BILLING_WEBHOOK_SECRET_MISSING",
                unavailable_reason=(
                    f"Live payment provider '{provider}' requires PAYMENT_WEBHOOK_SECRET."
                ),
            )
        return BillingCapabilities(
            release_mode="PAID_ENABLED",
            checkout_enabled=True,
            mock_confirm_enabled=False,
            provider=provider,
            status_message="Thanh toán Premium trực tuyến đã sẵn sàng.",
        )

    return BillingCapabilities(
        release_mode="PAID_ENABLED",
        checkout_enabled=False,
        mock_confirm_enabled=False,
        provider="none",
        status_message=PAID_UNAVAILABLE_STATUS_MESSAGE,
        unavailable_code="BILLING_PROVIDER_UNCONFIGURED",
        unavailable_reason=(
            f"Live payment provider '{provider or 'none'}' is not configured; "
            f"checkout is disabled (fail-closed)."
        ),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
