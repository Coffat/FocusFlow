import re
from typing import Any

# Regex patterns for PII masking and secret redaction (ADR-008 / BUSR-10)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Credit card numbers: 13-19 digits, optionally separated by single spaces or hyphens
_CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

# Phone numbers: international (+84..., +1...) or local (09..., 03..., (123) 456-7890)
_PHONE_RE = re.compile(
    r"(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)[\s.-]?|\b0\d{1,3}[\s.-]?|\b\d{3}[\s.-])\d{3,4}[\s.-]?\d{3,4}\b"
)

# Password / secret / API key / token assignments
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|mật\s*khẩu|secret|api[_-]?key|access[_-]?token|auth[_-]?token|private[_-]?key)"
    r"(\s*(?:=|:|là|is)\s*)(['\"]?[^\s,;'\"]+['\"]?)"
)

# Opening or closing <user_input> tags (including whitespace/attributes) for XML boundary injection neutralization
_USER_INPUT_TAG_RE = re.compile(
    r"<\s*(/?)\s*user_input(?:\s+[^>]*)?\s*>",
    re.IGNORECASE,
)

_SENSITIVE_DICT_KEYS: frozenset[str] = frozenset(
    {
        "email",
        "phone",
        "phone_number",
        "password",
        "password_hash",
        "secret",
        "api_key",
        "access_token",
        "refresh_token",
        "credit_card",
        "card_number",
        "oauth_refresh_token_encrypted",
        "token_hash",
    }
)


class PromptSanitizer:
    """Sanitizes learner input before sending to external LLM providers (ADR-008, BUSR-10).

    Responsibilities:
    1. Masks PII (emails, credit card numbers, phone numbers) and secret/password assignments.
    2. Neutralizes prompt-injection attempts by escaping any `<user_input>` or `</user_input>`
       tags inside user-supplied text.
    3. Wraps sanitized user text inside `<user_input>...</user_input>` XML delimiters.
    """

    @classmethod
    def mask_pii(cls, text: str) -> str:
        """Strip/mask PII and secret assignments from raw text without adding outer XML tags."""
        if not text:
            return ""

        sanitized = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
        sanitized = _SECRET_ASSIGNMENT_RE.sub(r"\1\2[REDACTED_SECRET]", sanitized)
        # Apply credit card masking before phone masking so 16-digit cards match as cards
        sanitized = _CREDIT_CARD_RE.sub("[REDACTED_CARD]", sanitized)
        sanitized = _PHONE_RE.sub("[REDACTED_PHONE]", sanitized)
        return sanitized

    @classmethod
    def escape_user_input_tags(cls, text: str) -> str:
        """Escape any `<user_input>` or `</user_input>` tags in user text to prevent boundary breakout."""
        if not text:
            return ""
        return _USER_INPUT_TAG_RE.sub(r"&lt;\1user_input&gt;", text)

    @classmethod
    def sanitize(cls, text: str, *, wrap_xml: bool = True) -> str:
        """Sanitize PII, escape `<user_input>` injection tags, and wrap in `<user_input>...</user_input>`."""
        masked = cls.mask_pii(text)
        escaped = cls.escape_user_input_tags(masked)
        if wrap_xml:
            return f"<user_input>{escaped}</user_input>"
        return escaped

    @classmethod
    def sanitize_text(cls, text: str, *, wrap_xml: bool = True) -> str:
        """Alias for sanitize()."""
        return cls.sanitize(text, wrap_xml=wrap_xml)

    @classmethod
    def sanitize_dict(cls, payload: dict[str, Any]) -> dict[str, Any]:
        """Recursively redact sensitive keys and sanitize string values in a dictionary."""
        cleaned: dict[str, Any] = {}
        for key, value in payload.items():
            if key.lower() in _SENSITIVE_DICT_KEYS:
                cleaned[key] = "[REDACTED]"
            elif isinstance(value, str):
                cleaned[key] = cls.escape_user_input_tags(cls.mask_pii(value))
            elif isinstance(value, dict):
                cleaned[key] = cls.sanitize_dict(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    cls.sanitize_dict(item)
                    if isinstance(item, dict)
                    else (
                        cls.escape_user_input_tags(cls.mask_pii(item))
                        if isinstance(item, str)
                        else item
                    )
                    for item in value
                ]
            else:
                cleaned[key] = value
        return cleaned
