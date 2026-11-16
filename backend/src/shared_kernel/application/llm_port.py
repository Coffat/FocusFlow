from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Sequence
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
