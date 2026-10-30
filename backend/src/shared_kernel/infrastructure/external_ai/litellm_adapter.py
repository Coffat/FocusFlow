import json
from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel

from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.config import get_settings


def _normalize_schema_and_validate(
    raw_data: dict[str, Any],
    response_schema: dict[str, Any] | type[Any] | None,
) -> dict[str, Any]:
    """Validate raw_data with Pydantic BaseModel if response_schema is a BaseModel subclass."""
    if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
        validated = response_schema.model_validate(raw_data)
        return validated.model_dump(mode="json")
    return raw_data


def _extract_json_schema(
    response_schema: dict[str, Any] | type[Any] | None,
) -> dict[str, Any]:
    if response_schema is None:
        return {}
    if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
        return response_schema.model_json_schema()
    if isinstance(response_schema, dict):
        return response_schema
    return {}


class MockLLMAdapter(LLMProviderPort):
    """Deterministic Mock LLM Adapter for offline Thesis Defense & CI testing (ADR-006)."""

    def __init__(self, canned_responses: list[dict[str, Any]] | None = None) -> None:
        self._canned_responses = list(canned_responses) if canned_responses else []

    async def generate_structured(
        self,
        prompt: str | None = None,
        system_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        *,
        user_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> tuple[dict[str, Any], int, int]:
        _ = (prompt, system_prompt, user_prompt, temperature)
        if self._canned_responses:
            raw_payload = self._canned_responses.pop(0)
            return _normalize_schema_and_validate(raw_payload, response_schema), 128, 256

        schema_dict = _extract_json_schema(response_schema)
        props = schema_dict.get("properties", {}) if isinstance(schema_dict, dict) else {}

        mock_payload: dict[str, Any] = {
            "status": "mock_generated",
            "summary": "Deterministic SRL study plan generated in offline mode.",
            "milestones": [
                {
                    "sequence_order": 1,
                    "title": "Nền tảng cốt lõi & Thiết lập môi trường",
                    "description": "Nắm vững kiến thức nền tảng và chuẩn bị công cụ thực hành.",
                },
                {
                    "sequence_order": 2,
                    "title": "Thực hành chuyên sâu & Xây dựng cấu trúc",
                    "description": "Áp dụng lý thuyết vào các bài tập thực tiễn có kiểm soát.",
                },
                {
                    "sequence_order": 3,
                    "title": "Tổng hợp, Kiểm thử & Đánh giá toàn diện",
                    "description": "Hoàn thiện dự án thực tế và tự đánh giá theo chuẩn SRL.",
                },
            ]
            if "milestones" in props and props.get("milestones", {}).get("minItems", 0) > 0
            else [],
        }

        if "tasks" in props and "tasks" not in mock_payload:
            mock_payload["tasks"] = []

        return _normalize_schema_and_validate(mock_payload, response_schema), 128, 256

    async def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        _ = (system_prompt, user_prompt, temperature)
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
        prompt: str | None = None,
        system_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        *,
        user_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> tuple[dict[str, Any], int, int]:
        effective_user_prompt = user_prompt if user_prompt is not None else (prompt or "")

        if self._settings.llm_provider.lower() == "mock":
            return await MockLLMAdapter().generate_structured(
                prompt=effective_user_prompt,
                system_prompt=system_prompt,
                response_schema=response_schema,
                user_prompt=effective_user_prompt,
                temperature=temperature,
            )

        from litellm import acompletion

        schema_dict = _extract_json_schema(response_schema)
        sys_content = system_prompt
        if schema_dict:
            sys_content = (
                f"{system_prompt}\n\nRespond strictly with JSON conforming to this schema:\n"
                f"{json.dumps(schema_dict, ensure_ascii=False)}"
            )

        response = await acompletion(
            model=self.model_identifier,
            messages=[
                {"role": "system", "content": sys_content},
                {"role": "user", "content": effective_user_prompt},
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
        parsed = json.loads(content)
        validated_dict = _normalize_schema_and_validate(parsed, response_schema)
        return validated_dict, prompt_tokens, completion_tokens

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
