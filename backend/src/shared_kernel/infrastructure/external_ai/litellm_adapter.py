import json
import re
from collections.abc import AsyncIterator
from datetime import date, timedelta
from typing import Any
from uuid import NAMESPACE_DNS, uuid5

from pydantic import BaseModel

from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.config import get_settings

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_SLOT_RE = re.compile(
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*:\s*(\d{2}:\d{2})-(\d{2}:\d{2})",
    re.IGNORECASE,
)

_WEEKDAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


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


def _build_mock_tasks_from_prompt(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Synthesize realistic, constraint-compliant study tasks from prompt context in offline mode."""
    found_uuids = list(dict.fromkeys(_UUID_RE.findall(text)))
    milestone_ids = (
        found_uuids[:5]
        if found_uuids
        else [str(uuid5(NAMESPACE_DNS, f"ms-{i}")) for i in range(1, 4)]
    )

    found_dates = _DATE_RE.findall(text)
    base_date = date(2026, 11, 2)
    if found_dates:
        try:
            base_date = date.fromisoformat(found_dates[0])
        except ValueError:
            base_date = date(2026, 11, 2)

    slot_matches = _SLOT_RE.findall(text)
    slots_by_day: dict[str, tuple[str, str]] = {}
    for d_name, s_time, e_time in slot_matches:
        d_key = d_name.lower()
        if d_key not in slots_by_day:
            slots_by_day[d_key] = (s_time, e_time)

    tasks: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []
    day_offset = 0

    for idx, mid in enumerate(milestone_ids):
        chosen_date = base_date + timedelta(days=day_offset)
        if slots_by_day:
            for step in range(14):
                candidate = base_date + timedelta(days=day_offset + step)
                wname = _WEEKDAY_NAMES[candidate.weekday()]
                if wname in slots_by_day:
                    chosen_date = candidate
                    day_offset = day_offset + step
                    break

        wname = _WEEKDAY_NAMES[chosen_date.weekday()]
        start_hhmm = "19:30"
        if wname in slots_by_day:
            start_hhmm = slots_by_day[wname][0]
        elif wname in ("saturday", "sunday"):
            start_hhmm = "14:00"

        sh, sm = (int(x) for x in start_hhmm.split(":"))
        duration_mins = 60
        total_end_m = sh * 60 + sm + duration_mins
        end_date = chosen_date + timedelta(days=total_end_m // 1440)
        eh = (total_end_m % 1440) // 60
        em = total_end_m % 60

        task_id = str(uuid5(NAMESPACE_DNS, f"mock-task-{mid}-{idx}"))
        tasks.append(
            {
                "task_id": task_id,
                "milestone_id": mid,
                "title": f"Phiên tự học chuyên sâu #{idx + 1}",
                "description": f"Thực hành và ghi chú chủ động cho cột mốc #{idx + 1} theo chu trình Zimmerman SRL.",
                "estimated_minutes": duration_mins,
                "scheduled_date": chosen_date.isoformat(),
                "scheduled_start": f"{chosen_date.isoformat()}T{sh:02d}:{sm:02d}:00+00:00",
                "scheduled_end": f"{end_date.isoformat()}T{eh:02d}:{em:02d}:00+00:00",
            }
        )
        if idx > 0:
            dependencies.append(
                {
                    "predecessor_id": tasks[idx - 1]["task_id"],
                    "successor_id": task_id,
                    "is_mandatory": True,
                }
            )
        day_offset += 1

    return tasks, dependencies


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
        _ = temperature
        if self._canned_responses:
            raw_payload = self._canned_responses.pop(0)
            return _normalize_schema_and_validate(raw_payload, response_schema), 128, 256

        effective_prompt = f"{system_prompt}\n{user_prompt or prompt or ''}"
        schema_dict = _extract_json_schema(response_schema)
        props = schema_dict.get("properties", {}) if isinstance(schema_dict, dict) else {}

        default_milestones = [
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

        mock_payload: dict[str, Any] = {
            "status": "mock_generated",
            "summary": "Deterministic SRL study plan generated in offline mode.",
            "milestones": (
                default_milestones
                if "milestones" in props
                and (props.get("milestones", {}).get("minItems", 0) > 0 or "tasks" not in props)
                else []
            ),
        }

        if "tasks" in props:
            if (
                "MILESTONE_IDS:" in effective_prompt
                or "GENERATE_PROPOSAL_TASKS" in effective_prompt
            ):
                tasks, deps = _build_mock_tasks_from_prompt(effective_prompt)
                mock_payload["tasks"] = tasks
                mock_payload["dependencies"] = deps
            elif "tasks" not in mock_payload:
                mock_payload["tasks"] = []

        if "score" in props and "advisory_warnings" in props:
            mock_payload["score"] = 0.92
            mock_payload["advisory_warnings"] = []

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
