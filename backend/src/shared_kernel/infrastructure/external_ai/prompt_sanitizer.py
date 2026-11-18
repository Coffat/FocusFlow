import re
from typing import Any

from src.shared_kernel.application.harness.untrusted_context import (
    SENSITIVE_DICT_KEYS,
    mask_pii_and_secrets,
    sanitize_untrusted_text,
)

_SENSITIVE_DICT_KEYS = SENSITIVE_DICT_KEYS


class PromptSanitizer:
    """Sanitizes learner input before sending to external LLM providers (ADR-008, BUSR-10).

    Delegates boundary escaping and PII masking to the shared untrusted context module.
    """

    @classmethod
    def mask_pii(cls, text: str) -> str:
        """Strip/mask PII and secret assignments from raw text without adding outer XML tags."""
        return mask_pii_and_secrets(text)

    @classmethod
    def escape_user_input_tags(cls, text: str) -> str:
        """Escape XML tags, script tags, injection directives, and fake section headers."""
        if not text:
            return ""
        return sanitize_untrusted_text(text, normalize_user_input_tag=True)

    @classmethod
    def sanitize(cls, text: str, *, wrap_xml: bool = True) -> str:
        """Sanitize PII, escape boundary injection tags, and wrap in `<user_input>...</user_input>`."""
        escaped = cls.escape_user_input_tags(text)
        if wrap_xml:
            return f"<user_input>{escaped}</user_input>"
        return escaped

    @classmethod
    def sanitize_text(cls, text: str, *, wrap_xml: bool = False) -> str:
        """Sanitize inline text without outer XML wrapper by default."""
        return cls.sanitize(text, wrap_xml=wrap_xml)

    @classmethod
    def sanitize_and_wrap(cls, tag_name: str, text: str) -> str:
        """Sanitize PII & prompt-injection sequences and wrap in `<tag_name>...</tag_name>`."""
        safe_tag = re.sub(r"[^a-zA-Z0-9_-]", "_", tag_name.strip()) or "user_input"
        inner = cls.sanitize(text, wrap_xml=False)
        return f"<{safe_tag}>{inner}</{safe_tag}>"

    @classmethod
    def sanitize_dict(cls, payload: dict[str, Any]) -> dict[str, Any]:
        """Recursively redact sensitive keys and sanitize string values in a dictionary."""
        cleaned: dict[str, Any] = {}
        for key, value in payload.items():
            if key.lower() in _SENSITIVE_DICT_KEYS:
                cleaned[key] = "[REDACTED]"
            elif isinstance(value, str):
                cleaned[key] = cls.escape_user_input_tags(value)
            elif isinstance(value, dict):
                cleaned[key] = cls.sanitize_dict(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    cls.sanitize_dict(item)
                    if isinstance(item, dict)
                    else (cls.escape_user_input_tags(item) if isinstance(item, str) else item)
                    for item in value
                ]
            else:
                cleaned[key] = value
        return cleaned
