from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol


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
    model_name: str = "gemini-2.5-flash"

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMProviderPort(Protocol):
    """Provider-agnostic Output Port for LLM Structured JSON & Streaming generation (ADR-006)."""

    async def generate_structured(
        self,
        prompt: str | None = None,
        system_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        *,
        user_prompt: str | None = None,
        temperature: float = 0.2,
        tools: list[LLMToolDeclarationDTO] | None = None,
        tool_executor: LLMToolExecutor | None = None,
        max_tool_calls: int = 4,
        thinking_level: str | None = None,
    ) -> tuple[dict[str, Any], int, int]:
        """Return (parsed_json_dict, prompt_tokens, completion_tokens).

        Supports passing `response_schema` as either a JSON Schema `dict` or a Pydantic
        `BaseModel` subclass, accepts either `user_prompt` or `prompt`, and supports
        optional read-only tool execution (`tools` + `tool_executor`) with `max_tool_calls`
        and Gemini thinking configuration (`thinking_level`).
        """
        ...

    def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        """Yield incremental text/JSON chunks for 2-Stage SSE Streaming (ADR-005)."""
        ...
