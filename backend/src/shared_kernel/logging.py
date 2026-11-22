from collections.abc import Mapping, MutableMapping
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
        "embedding_api_key",
        "gemini_api_key",
        "oauth_refresh_token_enc",
        "note_content",
        "email",
        "to_email",
        "otp_code",
        "authorization",
        "cookie",
        "fernet_key",
        "calendar_encryption_key",
        "google_client_secret",
        "payment_webhook_secret",
    }
)

_MAX_REDACTION_DEPTH = 16


def _redact_value(value: Any, *, _depth: int = 0) -> Any:
    """Recursively redact sensitive keys in nested mappings, lists, and tuples."""
    if _depth >= _MAX_REDACTION_DEPTH:
        return "[REDACTED_DEPTH_LIMIT]"
    if isinstance(value, Mapping):
        return {
            k: (
                "[REDACTED]"
                if isinstance(k, str) and k.lower() in SENSITIVE_KEYS
                else _redact_value(v, _depth=_depth + 1)
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(item, _depth=_depth + 1) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item, _depth=_depth + 1) for item in value)
    return value


def redact_pii_processor(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Redact PII and sensitive secrets recursively from structured logs."""
    event_dict["correlation_id"] = correlation_id_ctx.get()
    for key in list(event_dict.keys()):
        if isinstance(key, str) and key.lower() in SENSITIVE_KEYS:
            event_dict[key] = "[REDACTED]"
        else:
            event_dict[key] = _redact_value(event_dict[key])
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
