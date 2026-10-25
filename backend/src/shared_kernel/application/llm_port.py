from collections.abc import AsyncIterator
from typing import Any, Protocol


class LLMProviderPort(Protocol):
    """Provider-agnostic Output Port for LLM Structured JSON & Streaming generation (ADR-006)."""

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.2,
    ) -> tuple[dict[str, Any], int, int]:
        """Return (parsed_json_dict, prompt_tokens, completion_tokens)."""
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
