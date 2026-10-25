import json
from collections.abc import AsyncIterator
from typing import Any

from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.config import get_settings


class MockLLMAdapter(LLMProviderPort):
    """Deterministic Mock LLM Adapter for offline Thesis Defense & CI testing (ADR-006)."""

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.2,
    ) -> tuple[dict[str, Any], int, int]:
        mock_payload: dict[str, Any] = {
            "status": "mock_generated",
            "summary": "Deterministic SRL study plan generated in offline mode.",
            "milestones": [],
        }
        return mock_payload, 128, 256

    async def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        chunks = [
            '{"stage": "analyzing_goal", "progress": 25}',
            '{"stage": "validating_dag_and_availability", "progress": 75}',
            '{"stage": "completed", "progress": 100}',
        ]
        for chunk in chunks:
            yield chunk


class LiteLLMAdapter(LLMProviderPort):
    """Provider-agnostic LLM Adapter routing to Gemini, OpenAI, Claude, or Ollama via LiteLLM."""

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def model_identifier(self) -> str:
        provider = self._settings.llm_provider.lower()
        model = self._settings.llm_model
        if "/" in model:
            return model
        return f"{provider}/{model}"

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.2,
    ) -> tuple[dict[str, Any], int, int]:
        if self._settings.llm_provider.lower() == "mock":
            return await MockLLMAdapter().generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
                temperature=temperature,
            )

        from litellm import acompletion

        response = await acompletion(
            model=self.model_identifier,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            api_key=self._settings.llm_api_key,
            api_base=self._settings.llm_base_url or None,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        return json.loads(content), prompt_tokens, completion_tokens

    async def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        if self._settings.llm_provider.lower() == "mock":
            async for chunk in MockLLMAdapter().stream_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            ):
                yield chunk
            return

        from litellm import acompletion

        response = await acompletion(
            model=self.model_identifier,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            api_key=self._settings.llm_api_key,
            api_base=self._settings.llm_base_url or None,
            stream=True,
        )
        async for part in response:
            delta = part.choices[0].delta.content
            if delta:
                yield delta
