import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from pydantic import ValidationError


class AIErrorCategory(StrEnum):
    """Canonical 6-category error taxonomy for FocusFlow AI executions."""

    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    TIMEOUT = "TIMEOUT"
    GATEWAY_ERROR = "GATEWAY_ERROR"
    VALIDATION_GATE = "VALIDATION_GATE"
    QUOTA = "QUOTA"
    OTHER = "OTHER"


class SchemaMismatchError(ValueError):
    """Structured output schema mismatch error carrying adapter repair state."""

    code = "AI_SCHEMA_VALIDATION_ERROR"

    def __init__(
        self,
        message: str,
        *,
        already_repaired: bool = False,
        validation_summary: str = "",
        prompt_tokens: int = 0,
        output_tokens: int = 0,
        thinking_tokens: int = 0,
        model_id: str = "",
    ) -> None:
        super().__init__(message)
        self.already_repaired = already_repaired
        self.validation_summary = validation_summary or message
        self.prompt_tokens = prompt_tokens
        self.output_tokens = output_tokens
        self.thinking_tokens = thinking_tokens
        self.model_id = model_id


def format_concise_schema_errors(exc: BaseException, *, max_errors: int = 8) -> str:
    """Format ValidationError / JSONDecodeError / ValueError into concise field diagnostics."""
    if isinstance(exc, SchemaMismatchError) and exc.validation_summary:
        return exc.validation_summary[:600]
    if isinstance(exc, ValidationError):
        parts: list[str] = []
        for err in exc.errors(include_url=False, include_context=False, include_input=False)[
            :max_errors
        ]:
            loc = ".".join(str(p) for p in err.get("loc", ())) or "<root>"
            msg = str(err.get("msg", "invalid value"))
            err_type = str(err.get("type", ""))
            parts.append(f"{loc}: {msg}" + (f" [{err_type}]" if err_type else ""))
        return "; ".join(parts)[:600] or str(exc)[:600]
    if isinstance(exc, json.JSONDecodeError):
        return f"Invalid JSON at line {exc.lineno} col {exc.colno}: {exc.msg}"[:600]
    return str(exc)[:600]


_QUOTA_ERROR_CODES = frozenset(
    {"QUOTA", "QUOTA_EXCEEDED", "INSUFFICIENT_QUOTA", "AI_QUOTA_EXCEEDED"}
)
_VALIDATION_GATE_CODES = frozenset(
    {
        "VALIDATION_GATE",
        "VALIDATION_OVERLOAD",
        "DEPENDENCY_CYCLE_DETECTED",
        "INSUFFICIENT_TASKS",
    }
)
_GATEWAY_HTTP_STATUS_CODES = frozenset({400, 401, 403, 404, 408, 422, 429, 500, 502, 503, 504})
_GATEWAY_EXCEPTION_TYPES = frozenset(
    {
        "ServerError",
        "APIError",
        "ClientError",
        "APIConnectionError",
        "ServiceUnavailableError",
        "InternalServerError",
        "BadGatewayError",
        "GatewayTimeoutError",
        "RateLimitError",
        "AIServiceUnavailableError",
    }
)
_GATEWAY_MESSAGE_MARKERS = (
    "500",
    "502",
    "503",
    "504",
    "429",
    "400",
    "401",
    "403",
    "404",
    "408",
    "422",
    "stream interrupted",
    "servererror",
    "unavailable",
    "resource_exhausted",
    "rate limit",
    "high demand",
    "gateway",
    "unauthorized",
    "forbidden",
    "bad request",
    "invalid api key",
    "permission_denied",
    "permission denied",
    "connection",
    "not_found",
)
_SCHEMA_MESSAGE_MARKERS = (
    "ai_schema_validation_error",
    "missing required keys",
    "expected json object payload",
    "schema mismatch",
    "empty json response",
    "malformed_function_call",
    "validationerror",
    "jsondecodeerror",
)


def classify_ai_error(exc: BaseException) -> AIErrorCategory:
    """Classify an AI execution exception into the canonical 6-category taxonomy."""
    explicit_category = getattr(exc, "error_category", None)
    if isinstance(explicit_category, AIErrorCategory):
        return explicit_category

    code_upper = str(getattr(exc, "code", "") or "").strip().upper()
    exc_type_name = type(exc).__name__
    exc_type_upper = exc_type_name.upper()
    msg_lower = str(exc).lower()

    if "QUOTAEXCEEDED" in exc_type_upper or code_upper in _QUOTA_ERROR_CODES:
        return AIErrorCategory.QUOTA

    if "VALIDATIONGATE" in exc_type_upper or code_upper in _VALIDATION_GATE_CODES:
        return AIErrorCategory.VALIDATION_GATE

    if isinstance(exc, (SchemaMismatchError, ValidationError, json.JSONDecodeError)):
        return AIErrorCategory.SCHEMA_MISMATCH

    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or "TIMEOUT" in exc_type_upper:
        return AIErrorCategory.TIMEOUT

    status_code = getattr(exc, "status_code", None)
    if status_code is None and isinstance(getattr(exc, "code", None), int):
        status_code = getattr(exc, "code", None)
    if isinstance(status_code, int) and status_code in _GATEWAY_HTTP_STATUS_CODES:
        return AIErrorCategory.GATEWAY_ERROR

    if any(marker in msg_lower for marker in _SCHEMA_MESSAGE_MARKERS):
        return AIErrorCategory.SCHEMA_MISMATCH

    if isinstance(exc, ValueError) and any(
        marker in msg_lower
        for marker in ("json", "schema", "validation", "empty", "malformed", "parse")
    ):
        return AIErrorCategory.SCHEMA_MISMATCH

    if any(
        marker in msg_lower
        for marker in (
            "timeout",
            "timed out",
            "time budget",
            "quá thời gian chờ",
            "exceeded 55 seconds",
        )
    ):
        return AIErrorCategory.TIMEOUT

    if isinstance(exc, PermissionError) and not any(
        marker in msg_lower
        for marker in ("401", "403", "unauthorized", "forbidden", "permission_denied", "api key")
    ):
        return AIErrorCategory.OTHER

    if (
        isinstance(exc, ConnectionError)
        or (isinstance(exc, OSError) and not isinstance(exc, PermissionError))
        or exc_type_name in _GATEWAY_EXCEPTION_TYPES
        or any(marker in msg_lower for marker in _GATEWAY_MESSAGE_MARKERS)
    ):
        return AIErrorCategory.GATEWAY_ERROR

    return AIErrorCategory.OTHER


@dataclass(frozen=True, slots=True)
class LLMToolDeclarationDTO:
    """Provider-agnostic read-only tool declaration for structured LLM calls."""

    name: str
    description: str
    parameters_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LLMToolCallResultDTO:
    """Audit record of a single read-only tool invocation during an LLM turn."""

    tool_name: str
    arguments: dict[str, Any]
    output: dict[str, Any]


LLMToolExecutor = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(frozen=True, slots=True)
class LLMUsageMetadata:
    """Token usage and model metadata returned from an LLM invocation."""

    prompt_tokens: int
    completion_tokens: int
    thinking_tokens: int = 0
    model_name: str = "gemini-3.8-flash"

    @property
    def output_tokens(self) -> int:
        return self.completion_tokens

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True, slots=True)
class LLMGenerationResult:
    """Structured generation result unpackable as `(payload, prompt_tokens, output_tokens)`."""

    payload: dict[str, Any]
    prompt_tokens: int
    output_tokens: int
    thinking_tokens: int = 0
    model_id: str = "gemini-3.8-flash"
    raw_tool_results: tuple[LLMToolCallResultDTO, ...] = ()
    repair_attempts: int = 0
    error_category: AIErrorCategory | None = None

    @property
    def value(self) -> dict[str, Any]:
        return self.payload

    @property
    def completion_tokens(self) -> int:
        return self.output_tokens

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.output_tokens

    def __iter__(self) -> Iterator[Any]:
        yield self.payload
        yield self.prompt_tokens
        yield self.output_tokens

    def __len__(self) -> int:
        return 3

    def __getitem__(self, index: int) -> Any:
        return (self.payload, self.prompt_tokens, self.output_tokens)[index]


class LLMProviderPort(Protocol):
    """Provider-agnostic Output Port for LLM Structured JSON & Streaming generation (ADR-006)."""

    @property
    def supports_native_structured_output(self) -> bool:
        """Whether this provider natively enforces JSON Schema at generation time."""
        return True

    async def generate_structured(
        self,
        *,
        system_prompt: str = "",
        user_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        tools: Sequence[LLMToolDeclarationDTO | dict[str, Any]] | None = None,
        tool_executor: LLMToolExecutor | None = None,
        max_tool_calls: int = 2,
        thinking_level: str | None = None,
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> tuple[dict[str, Any], int, int] | LLMGenerationResult:
        """Return structured JSON result with prompt, output (candidate + thinking), and model metadata."""
        ...

    def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:
        """Yield incremental text/JSON chunks for 2-Stage SSE Streaming (ADR-005)."""
        ...
