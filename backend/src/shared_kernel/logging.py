from collections.abc import MutableMapping
from contextvars import ContextVar
from typing import Any

import structlog

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="system")

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "secret_key",
        "llm_api_key",
        "oauth_refresh_token_enc",
        "note_content",
    }
)


def redact_pii_processor(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Redact PII and sensitive secrets from structured logs."""
    event_dict["correlation_id"] = correlation_id_ctx.get()
    for key in list(event_dict.keys()):
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging() -> None:
    """Configure structlog with JSON output, correlation_id, and PII redaction."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_pii_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),
        cache_logger_on_first_use=True,
    )
