import asyncio
import json
import os
import re
from collections.abc import AsyncIterator, Sequence
from typing import Any

from pydantic import BaseModel

from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMProviderPort,
    LLMToolCallResultDTO,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
)
from src.shared_kernel.config import get_settings


def _normalize_schema_and_validate(
    raw_data: Any,
    response_schema: dict[str, Any] | type[Any] | None,
) -> dict[str, Any]:
    """Validate raw_data with Pydantic BaseModel if response_schema is a BaseModel subclass,
    or ensure dict structure if response_schema is a dict/schema definition."""
    if isinstance(raw_data, list):
        if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
            fields = getattr(response_schema, "model_fields", {})
            if "questions" in fields:
                raw_data = {"questions": raw_data}
            elif "milestones" in fields:
                raw_data = {"milestones": raw_data}
            elif "tasks" in fields:
                raw_data = {"tasks": raw_data, "dependencies": []}
            elif len(fields) == 1:
                single_key = next(iter(fields))
                raw_data = {single_key: raw_data}
            else:
                raw_data = {"items": raw_data}
        elif isinstance(response_schema, dict):
            props = response_schema.get("properties", {})
            if "milestones" in props:
                raw_data = {"milestones": raw_data}
            elif "tasks" in props:
                raw_data = {"tasks": raw_data, "dependencies": []}
            elif "questions" in props:
                raw_data = {"questions": raw_data}
            elif len(props) == 1:
                raw_data = {next(iter(props)): raw_data}
            else:
                raw_data = {"items": raw_data}
        else:
            raw_data = {"items": raw_data}

    if isinstance(raw_data, dict):
        raw_data = dict(raw_data)
        if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
            fields = getattr(response_schema, "model_fields", {})
            for target_field in ("questions", "milestones", "tasks"):
                if target_field in fields and target_field not in raw_data:
                    for alt in ("data", "result", "items", "list", f"{target_field}_list"):
                        if isinstance(raw_data.get(alt), list):
                            raw_data[target_field] = raw_data[alt]
                            break
            if "milestones" in fields:
                raw_data.setdefault(
                    "scope_summary",
                    str(raw_data.get("summary") or "Lộ trình cột mốc thích ứng theo mục tiêu."),
                )
                raw_data.setdefault("deferred_scope", [])
            if "score" in fields and "issues" in fields and "tasks" not in fields:
                raw_score = raw_data.get("score")
                if raw_score is None and isinstance(raw_data.get("pedagogical_score"), int | float):
                    raw_score = raw_data["pedagogical_score"]
                if isinstance(raw_score, float) and 0.0 < raw_score <= 1.0:
                    raw_data["score"] = int(round(raw_score * 100))
                elif isinstance(raw_score, int | float):
                    raw_data["score"] = int(round(float(raw_score)))
                raw_data.setdefault("issues", [])
        elif isinstance(response_schema, dict):
            props = response_schema.get("properties", {})
            for target_prop in ("questions", "milestones", "tasks"):
                if target_prop in props and target_prop not in raw_data:
                    for alt in ("data", "result", "items", "list", f"{target_prop}_list"):
                        if isinstance(raw_data.get(alt), list):
                            raw_data[target_prop] = raw_data[alt]
                            break

    if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
        validated = response_schema.model_validate(raw_data)
        return validated.model_dump(mode="json")
    return raw_data if isinstance(raw_data, dict) else {"data": raw_data}


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


def _tool_name(tool: LLMToolDeclarationDTO | dict[str, Any]) -> str:
    if isinstance(tool, dict):
        return str(tool.get("name", ""))
    return tool.name


def _tool_description(tool: LLMToolDeclarationDTO | dict[str, Any]) -> str:
    if isinstance(tool, dict):
        return str(tool.get("description", ""))
    return tool.description


def _tool_parameters_schema(tool: LLMToolDeclarationDTO | dict[str, Any]) -> dict[str, Any]:
    if isinstance(tool, dict):
        raw = tool.get("parameters_schema") or tool.get("parameters") or {}
        return dict(raw) if isinstance(raw, dict) else {}
    return dict(tool.parameters_schema)


def _normalize_thinking_level(raw_level: str | None, default_level: str = "MEDIUM") -> str:
    level = (raw_level or default_level or "MEDIUM").strip().upper()
    if level not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError(
            f"Unsupported thinking_level {raw_level!r}; allowed values are LOW, MEDIUM, HIGH."
        )
    return level


class LiteLLMAdapter(LLMProviderPort):
    """Provider-agnostic LLM Adapter routing to Gemini 3.8 Flash (google-genai) or LiteLLM."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self.model_used: str = self._settings.llm_model.split("/")[-1]
        self.last_model_used: str = self.model_used
        self.degraded_model_used: bool = False
        self.last_degraded_model_used: bool = False

    @property
    def supports_native_structured_output(self) -> bool:
        provider = self._settings.llm_provider.strip().lower()
        return provider == "gemini"

    def _validate_provider_config(self) -> None:
        provider = (self._settings.llm_provider or "").strip().lower()
        if not provider or provider in ("mock", "local_mock"):
            raise RuntimeError(
                f"AI_PROVIDER_NOT_CONFIGURED: Unsupported llm_provider={self._settings.llm_provider!r}. "
                "Configure a real provider (e.g. 'gemini', 'openai', 'anthropic') and valid LLM_API_KEY."
            )
        base_url = (getattr(self._settings, "llm_base_url", "") or "").strip()
        if provider == "gemini" and not base_url:
            raise RuntimeError(
                "AI_PROVIDER_NOT_CONFIGURED: Missing LLM_BASE_URL for cobhub gateway."
            )
        api_key = (getattr(self._settings, "llm_api_key", "") or "").strip()
        if not base_url and api_key in ("", "mock-key", "your-api-key"):
            raise RuntimeError(
                "AI_PROVIDER_NOT_CONFIGURED: Missing valid LLM_API_KEY (and no LLM_BASE_URL configured)."
            )

    @property
    def model_identifier(self) -> str:
        provider = self._settings.llm_provider.lower()
        model = self._settings.llm_model
        if "/" in model:
            return model
        return f"{provider}/{model}"

    def _should_use_google_genai_sdk(self) -> bool:
        return self._settings.llm_provider.strip().lower() == "gemini"

    def _resolve_base_url(self) -> str | None:
        base_url = (getattr(self._settings, "llm_base_url", "") or "").strip() or None
        if base_url and (os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_DOCKER")):
            base_url = re.sub(
                r"^http://(127\.0\.0\.1|localhost)(:\d+)",
                r"http://host.docker.internal\2",
                base_url,
            )
        return base_url

    def _resolve_candidate_models(self, thinking_level: str | None) -> tuple[list[str], set[str]]:
        effective_level = _normalize_thinking_level(
            thinking_level,
            getattr(self._settings, "llm_thinking_level", "MEDIUM"),
        )
        default_model = (getattr(self._settings, "llm_model", "") or "gemini-3.8-flash").split("/")[
            -1
        ].strip() or "gemini-3.8-flash"
        tier_attr = {
            "LOW": "llm_model_low",
            "MEDIUM": "llm_model_medium",
            "HIGH": "llm_model_high",
        }.get(effective_level, "llm_model_medium")
        if hasattr(self._settings, tier_attr):
            raw_tier_model = getattr(self._settings, tier_attr, "") or ""
            tier_model = raw_tier_model.split("/")[-1].strip() or "gemini-3.8-flash"
        else:
            tier_model = default_model

        candidates: list[str] = [tier_model]
        if default_model and default_model not in candidates:
            candidates.append(default_model)

        return candidates, set()

    async def _generate_with_google_genai(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | type[Any] | None,
        tools: Sequence[LLMToolDeclarationDTO | dict[str, Any]] | None,
        tool_executor: LLMToolExecutor | None,
        max_tool_calls: int,
        thinking_level: str | None,
    ) -> LLMGenerationResult:
        from google import genai
        from google.genai import types

        base_url = self._resolve_base_url()
        if not base_url:
            raise RuntimeError(
                "AI_PROVIDER_NOT_CONFIGURED: Missing LLM_BASE_URL for cobhub gateway."
            )
        http_opts = types.HttpOptions(
            base_url=base_url,
            api_version="v1beta",
            retry_options=types.HttpRetryOptions(attempts=1),
        )
        api_key = (self._settings.llm_api_key or "").strip() or "antigravity-proxy-key"
        client = genai.Client(
            api_key=api_key,
            http_options=http_opts,
        )
        effective_level = _normalize_thinking_level(
            thinking_level,
            getattr(self._settings, "llm_thinking_level", "MEDIUM"),
        )
        candidate_models, degraded_set = self._resolve_candidate_models(effective_level)
        preferred_model: str | None = None

        async def _call_model(
            contents: Any,
            config: Any,
            *,
            call_timeout: float = 35.0,
            parse_json_fn: Any | None = None,
        ) -> Any:
            nonlocal preferred_model
            ordered_candidates = list(candidate_models)
            if preferred_model and preferred_model in ordered_candidates:
                ordered_candidates.remove(preferred_model)
                ordered_candidates.insert(0, preferred_model)

            last_err: Exception | None = None
            for cand in ordered_candidates:
                try:
                    resp = await asyncio.wait_for(
                        client.aio.models.generate_content(
                            model=cand,
                            contents=contents,
                            config=config,
                        ),
                        timeout=call_timeout,
                    )
                    if parse_json_fn is not None:
                        parsed = parse_json_fn(resp)
                        preferred_model = cand
                        self.model_used = cand
                        self.last_model_used = cand
                        is_degraded = cand in degraded_set
                        self.degraded_model_used = is_degraded
                        self.last_degraded_model_used = is_degraded
                        return resp, parsed
                    preferred_model = cand
                    self.model_used = cand
                    self.last_model_used = cand
                    is_degraded = cand in degraded_set
                    self.degraded_model_used = is_degraded
                    self.last_degraded_model_used = is_degraded
                    return resp
                except TimeoutError as e:
                    last_err = e
                    continue
                except (json.JSONDecodeError, ValueError) as e:
                    if parse_json_fn is not None:
                        last_err = e
                        continue
                    raise
                except Exception as e:
                    err_str = str(e)
                    last_err = e
                    if (
                        "503" in err_str
                        or "UNAVAILABLE" in err_str
                        or "high demand" in err_str
                        or "RESOURCE_EXHAUSTED" in err_str
                        or "429" in err_str
                        or "quota" in err_str.lower()
                        or "404" in err_str
                        or "NOT_FOUND" in err_str
                    ):
                        continue
                    raise
            if last_err is not None:
                raise last_err
            raise RuntimeError("No candidate models available for Google GenAI")

        schema_dict = _extract_json_schema(response_schema)
        tool_thinking_level = "LOW" if effective_level in ("LOW", "MEDIUM") else "MEDIUM"

        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_thinking_tokens = 0
        tool_evidence_blocks: list[str] = []
        tool_call_records: list[LLMToolCallResultDTO] = []

        if tools and tool_executor is not None and max_tool_calls > 0:
            fn_decls = [
                types.FunctionDeclaration(
                    name=_tool_name(t),
                    description=_tool_description(t),
                    parameters_json_schema=_tool_parameters_schema(t),
                )
                for t in tools
            ]
            tool_cfg = types.GenerateContentConfig(
                system_instruction=system_prompt or None,
                tools=[types.Tool(function_declarations=fn_decls)],
                thinking_config=types.ThinkingConfig(
                    include_thoughts=False,
                    thinking_level=tool_thinking_level,  # type: ignore[arg-type]
                ),
            )
            contents: list[Any] = [user_prompt]
            calls_executed = 0

            while calls_executed < max_tool_calls:
                resp = await _call_model(
                    contents=contents,
                    config=tool_cfg,
                    call_timeout=18.0,
                )
                usage = getattr(resp, "usage_metadata", None)
                if usage is not None:
                    total_prompt_tokens += int(getattr(usage, "prompt_token_count", 0) or 0)
                    cand_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
                    thought_tokens = int(getattr(usage, "thoughts_token_count", 0) or 0)
                    total_completion_tokens += cand_tokens + thought_tokens
                    total_thinking_tokens += thought_tokens

                fn_calls = list(getattr(resp, "function_calls", None) or [])
                candidates_list = getattr(resp, "candidates", None) or []
                model_content = (
                    getattr(candidates_list[0], "content", None) if candidates_list else None
                )
                if not fn_calls and model_content is not None:
                    for part in getattr(model_content, "parts", None) or []:
                        part_fc = getattr(part, "function_call", None)
                        if part_fc is not None:
                            fn_calls.append(part_fc)

                if not fn_calls:
                    break

                # Preserve model turn (including function_call id/name/args and thought_signature)
                if model_content is not None:
                    contents.append(model_content)
                else:
                    preserved_calls = []
                    for fc in fn_calls:
                        fc_entry: dict[str, Any] = {
                            "id": getattr(fc, "id", None),
                            "name": str(getattr(fc, "name", "") or ""),
                            "args": dict(getattr(fc, "args", None) or {}),
                        }
                        if getattr(fc, "thought_signature", None) is not None:
                            fc_entry["thought_signature"] = getattr(fc, "thought_signature", None)
                        preserved_calls.append(fc_entry)
                    contents.append({"role": "model", "function_calls": preserved_calls})

                tool_response_parts: list[Any] = []
                for fc in fn_calls:
                    if calls_executed >= max_tool_calls:
                        break
                    fc_id = getattr(fc, "id", None)
                    fc_name = str(getattr(fc, "name", "") or "")
                    raw_args = getattr(fc, "args", None) or {}
                    fc_args = dict(raw_args) if isinstance(raw_args, dict) else {}
                    tool_output = await tool_executor(fc_name, fc_args)
                    calls_executed += 1
                    normalized_output = (
                        tool_output if isinstance(tool_output, dict) else {"result": tool_output}
                    )
                    tool_call_records.append(
                        LLMToolCallResultDTO(
                            tool_name=fc_name,
                            arguments=fc_args,
                            output=normalized_output,
                        )
                    )
                    tool_evidence_blocks.append(
                        f"[TOOL_RESULT name={fc_name}]\n"
                        f"{json.dumps(normalized_output, ensure_ascii=False)}"
                    )
                    try:
                        fn_resp_part = types.Part.from_function_response(
                            name=fc_name,
                            response=normalized_output,
                        )
                        fn_resp = fn_resp_part.function_response
                        if fc_id is not None and fn_resp is not None:
                            try:
                                fn_resp.id = str(fc_id)
                            except Exception:
                                pass
                        tool_response_parts.append(fn_resp_part)
                    except Exception:
                        tool_response_parts.append(
                            {
                                "function_response": {
                                    "id": fc_id,
                                    "name": fc_name,
                                    "response": normalized_output,
                                }
                            }
                        )

                if tool_response_parts:
                    try:
                        contents.append(types.Content(role="user", parts=tool_response_parts))
                    except Exception:
                        contents.append({"role": "user", "parts": tool_response_parts})

        final_user_prompt = user_prompt
        if tool_evidence_blocks:
            final_user_prompt = f"{user_prompt}\n\n[TOOL_EXECUTION_RESULTS]\n" + "\n".join(
                tool_evidence_blocks
            )

        final_system_instruction = (
            f"{system_prompt}\n\n"
            "[FINAL_OUTPUT_STAGE]: KHÔNG gọi thêm bất kỳ tool/function call nào ở bước này. "
            "Chỉ xuất DUY NHẤT JSON hợp lệ theo schema."
            if system_prompt
            else (
                "[FINAL_OUTPUT_STAGE]: KHÔNG gọi thêm bất kỳ tool/function call nào ở bước này. "
                "Chỉ xuất DUY NHẤT JSON hợp lệ theo schema."
            )
        )
        json_cfg = types.GenerateContentConfig(
            system_instruction=final_system_instruction,
            response_mime_type="application/json",
            response_json_schema=schema_dict if schema_dict else None,
            max_output_tokens=32768,
            thinking_config=types.ThinkingConfig(
                include_thoughts=False,
                thinking_level=effective_level,  # type: ignore[arg-type]
            ),
        )

        def _parse_json_response(resp_obj: Any) -> Any:
            raw = (getattr(resp_obj, "text", None) or "").strip()
            if not raw:
                candidates_list = getattr(resp_obj, "candidates", None) or []
                finish_reason = (
                    getattr(candidates_list[0], "finish_reason", None) if candidates_list else None
                )
                raise ValueError(f"Empty JSON response from model (finish_reason={finish_reason})")
            clean = raw
            if clean.startswith("```json"):
                clean = clean[7:]
            elif clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()
            try:
                return json.loads(clean)
            except Exception:
                json_match = re.search(r"(\{.*\})", clean, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
                json_list_match = re.search(r"(\[.*\])", clean, re.DOTALL)
                if json_list_match:
                    return json.loads(json_list_match.group(1))
                raise

        final_call_timeout = {"LOW": 25.0, "MEDIUM": 35.0, "HIGH": 35.0}.get(effective_level, 35.0)
        final_resp, parsed = await _call_model(
            contents=final_user_prompt,
            config=json_cfg,
            call_timeout=final_call_timeout,
            parse_json_fn=_parse_json_response,
        )
        usage = getattr(final_resp, "usage_metadata", None)
        if usage is not None:
            total_prompt_tokens += int(getattr(usage, "prompt_token_count", 0) or 0)
            cand_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
            thought_tokens = int(getattr(usage, "thoughts_token_count", 0) or 0)
            total_completion_tokens += cand_tokens + thought_tokens
            total_thinking_tokens += thought_tokens

        validated = _normalize_schema_and_validate(parsed, response_schema)
        return LLMGenerationResult(
            payload=validated,
            prompt_tokens=total_prompt_tokens,
            output_tokens=total_completion_tokens,
            thinking_tokens=total_thinking_tokens,
            model_id=self.last_model_used,
            raw_tool_results=tuple(tool_call_records),
        )

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
    ) -> LLMGenerationResult:
        if thinking_level is not None:
            _normalize_thinking_level(thinking_level)

        self._validate_provider_config()

        if self._should_use_google_genai_sdk():
            return await self._generate_with_google_genai(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
                tools=tools,
                tool_executor=tool_executor,
                max_tool_calls=max_tool_calls,
                thinking_level=thinking_level,
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
                {"role": "user", "content": user_prompt},
            ],
            api_key=self._settings.llm_api_key,
            api_base=self._resolve_base_url(),
            response_format={"type": "json_object"},
        )
        content = (response.choices[0].message.content or "{}").strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE).strip()
        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        parsed = json.loads(content)
        validated_dict = _normalize_schema_and_validate(parsed, response_schema)
        self.model_used = self.model_identifier.split("/")[-1]
        self.last_model_used = self.model_used
        return LLMGenerationResult(
            payload=validated_dict,
            prompt_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            thinking_tokens=0,
            model_id=self.last_model_used,
        )

    async def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:
        self._validate_provider_config()

        from litellm import acompletion

        response = await acompletion(
            model=self.model_identifier,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            api_key=self._settings.llm_api_key,
            api_base=self._resolve_base_url(),
            stream=True,
        )
        async for part in response:
            delta = part.choices[0].delta.content
            if delta:
                yield delta
