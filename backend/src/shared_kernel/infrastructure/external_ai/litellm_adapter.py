import asyncio
import json
import os
import re
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ValidationError

from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMProviderPort,
    LLMToolCallResultDTO,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
    SchemaMismatchError,
    format_concise_schema_errors,
)
from src.shared_kernel.config import get_settings

logger = structlog.get_logger(__name__)

_DEFAULT_PROBE_TIMEOUT_SECONDS = 8.0
_LOW_THINKING_MAX_TOKENS = 300


class _GatewaySchemaProbeModel(BaseModel):
    probe_status: Literal["OK"]
    probe_code: int


@dataclass(frozen=True, slots=True)
class CobhubCapabilityProbeResult:
    """Result of probing cobhub gateway schema enforcement & low-thinking behavior."""

    base_url: str
    requested_low_model: str
    actual_model_id: str
    schema_enforced_detected: bool
    low_model_thinking_tokens: int
    low_thinking_is_low: bool
    configured_schema_enforced: bool = False
    mismatches: tuple[str, ...] = ()
    probe_succeeded: bool = True
    error: str | None = None
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "degraded" if (not self.probe_succeeded or self.mismatches) else "ok",
            "probe_succeeded": self.probe_succeeded,
            "base_url": self.base_url,
            "requested_low_model": self.requested_low_model,
            "actual_model_id": self.actual_model_id,
            "schema_enforced_detected": self.schema_enforced_detected,
            "configured_schema_enforced": self.configured_schema_enforced,
            "low_model_thinking_tokens": self.low_model_thinking_tokens,
            "low_thinking_is_low": self.low_thinking_is_low,
            "mismatches": list(self.mismatches),
            "error": self.error,
            "cached": self.cached,
        }


_COBHUB_PROBE_CACHE: dict[tuple[str, str], CobhubCapabilityProbeResult] = {}


def clear_cobhub_capability_probe_cache() -> None:
    """Clear cached cobhub capability probe results."""
    _COBHUB_PROBE_CACHE.clear()


def _rewrite_docker_localhost(base_url: str | None) -> str | None:
    cleaned = (base_url or "").strip() or None
    if cleaned and (os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_DOCKER")):
        cleaned = re.sub(
            r"^http://(127\.0\.0\.1|localhost)(:\d+)",
            r"http://host.docker.internal\2",
            cleaned,
        )
    return cleaned


def _parse_json_text(raw: str) -> Any:
    clean = raw.strip()
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


def _resolve_schema_ref(
    node: dict[str, Any],
    defs: dict[str, Any],
    seen_refs: frozenset[str],
) -> tuple[dict[str, Any], frozenset[str], str | None]:
    ref = node.get("$ref")
    if not isinstance(ref, str) or not ref:
        return node, seen_refs, None
    if ref in seen_refs:
        return {}, seen_refs, ref.rsplit("/", 1)[-1]
    ref_name = ref.rsplit("/", 1)[-1]
    target = defs.get(ref_name)
    if isinstance(target, dict):
        return target, seen_refs | {ref}, None
    return node, seen_refs, ref_name


def _format_compact_type(
    node: dict[str, Any],
    defs: dict[str, Any],
    seen_refs: frozenset[str],
    indent: int,
) -> str:
    resolved, next_seen, cycle_name = _resolve_schema_ref(node, defs, seen_refs)
    if cycle_name is not None and not resolved:
        return f"object({cycle_name})"

    if "const" in resolved:
        return f"const({json.dumps(resolved['const'], ensure_ascii=False)})"
    if "enum" in resolved and isinstance(resolved["enum"], list):
        enum_vals = ", ".join(json.dumps(v, ensure_ascii=False) for v in resolved["enum"])
        base = str(resolved.get("type") or "enum")
        return f"{base}[enum=({enum_vals})]"

    for union_key in ("anyOf", "oneOf"):
        variants = resolved.get(union_key)
        if isinstance(variants, list) and variants:
            parts = [
                _format_compact_type(v, defs, next_seen, indent)
                for v in variants
                if isinstance(v, dict)
            ]
            return " | ".join(parts) if parts else "any"

    schema_type = resolved.get("type")
    if isinstance(schema_type, list):
        return " | ".join(str(t) for t in schema_type)

    if schema_type == "array" or "items" in resolved:
        arr_constraints: list[str] = []
        if "minItems" in resolved:
            arr_constraints.append(f"minItems={resolved['minItems']}")
        if "maxItems" in resolved:
            arr_constraints.append(f"maxItems={resolved['maxItems']}")
        items_node = resolved.get("items")
        inner = (
            _format_compact_type(items_node, defs, next_seen, indent)
            if isinstance(items_node, dict)
            else "any"
        )
        constraint_str = f"[{', '.join(arr_constraints)}]" if arr_constraints else ""
        return f"array{constraint_str}<{inner}>"

    if schema_type == "object" or "properties" in resolved:
        props = resolved.get("properties")
        if not isinstance(props, dict) or not props:
            return "object"
        req_set = {str(r) for r in (resolved.get("required") or [])}
        pad = "  " * (indent + 1)
        close_pad = "  " * indent
        lines: list[str] = ["object {"]
        for key, prop_schema in props.items():
            req_tag = " (required)" if key in req_set else ""
            prop_str = (
                _format_compact_type(prop_schema, defs, next_seen, indent + 1)
                if isinstance(prop_schema, dict)
                else "any"
            )
            lines.append(f"{pad}{key}{req_tag}: {prop_str}")
        lines.append(f"{close_pad}}}")
        return "\n".join(lines)

    base_type = str(schema_type or "any")
    constraints: list[str] = []
    if "minimum" in resolved:
        constraints.append(f"min={resolved['minimum']}")
    elif "exclusiveMinimum" in resolved:
        constraints.append(f"min>{resolved['exclusiveMinimum']}")
    if "maximum" in resolved:
        constraints.append(f"max={resolved['maximum']}")
    elif "exclusiveMaximum" in resolved:
        constraints.append(f"max<{resolved['exclusiveMaximum']}")
    if constraints:
        return f"{base_type}({', '.join(constraints)})"
    return base_type


def render_compact_schema_spec(schema_dict: dict[str, Any]) -> str:
    """Render a compact, token-efficient schema spec (fields, types, required, enum, min/max, items)."""
    if not schema_dict:
        return ""
    raw_defs = schema_dict.get("$defs") or schema_dict.get("definitions") or {}
    defs = raw_defs if isinstance(raw_defs, dict) else {}
    body = _format_compact_type(schema_dict, defs, frozenset(), 0)
    if not body or body == "any":
        return ""
    return f"[COMPACT_JSON_SCHEMA]\nReturn ONLY a JSON matching:\n{body}"


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
                "AI_PROVIDER_NOT_CONFIGURED: Thiếu LLM_BASE_URL cho gateway cobhub. "
                "Hãy đặt LLM_BASE_URL trong .env (xem .env.example)."
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
        return _rewrite_docker_localhost(getattr(self._settings, "llm_base_url", ""))

    def _resolve_thinking_control(self) -> str:
        raw = str(getattr(self._settings, "llm_thinking_control", "model_suffix") or "model_suffix")
        mode = raw.strip().lower()
        return mode if mode in {"model_suffix", "param"} else "model_suffix"

    def _resolve_candidate_models(self, thinking_level: str | None) -> tuple[list[str], set[str]]:
        effective_level = _normalize_thinking_level(
            thinking_level,
            getattr(self._settings, "llm_thinking_level", "MEDIUM"),
        )
        default_model = (
            getattr(self._settings, "llm_model", "") or "gemini-3.8-flash-medium"
        ).split("/")[-1].strip() or "gemini-3.8-flash-medium"
        if self._resolve_thinking_control() == "param":
            candidates = [default_model]
        else:
            tier_attr = {
                "LOW": "llm_model_low",
                "MEDIUM": "llm_model_medium",
                "HIGH": "llm_model_high",
            }.get(effective_level, "llm_model_medium")
            if hasattr(self._settings, tier_attr):
                raw_tier_model = getattr(self._settings, tier_attr, "") or ""
                tier_model = raw_tier_model.split("/")[-1].strip() or default_model
            else:
                tier_model = default_model

            candidates = [tier_model]
            if default_model and default_model not in candidates:
                candidates.append(default_model)

        raw_fallbacks = str(getattr(self._settings, "llm_fallback_models", "") or "")
        for raw_item in raw_fallbacks.split(","):
            fallback_model = raw_item.strip()
            if fallback_model and fallback_model not in candidates:
                candidates.append(fallback_model)

        return candidates, set()

    @staticmethod
    def build_google_genai_client(api_key: str, base_url: str) -> Any:
        """Build a google-genai Client configured for the cobhub proxy endpoint."""
        from google import genai
        from google.genai import types

        http_opts = types.HttpOptions(
            base_url=base_url,
            api_version="v1beta",
            retry_options=types.HttpRetryOptions(attempts=1),
        )
        effective_key = (api_key or "").strip() or "antigravity-proxy-key"
        return genai.Client(
            api_key=effective_key,
            http_options=http_opts,
        )

    @staticmethod
    def build_generate_content_config(
        *,
        system_instruction: str | None = None,
        response_mime_type: str | None = None,
        response_json_schema: dict[str, Any] | None = None,
        max_output_tokens: int | None = None,
        thinking_level: str | None = None,
        tools: list[Any] | None = None,
        include_thoughts: bool = False,
    ) -> Any:
        """Build a google.genai.types.GenerateContentConfig preserving adapter defaults."""
        from google.genai import types

        kwargs: dict[str, Any] = {}
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        if response_mime_type is not None:
            kwargs["response_mime_type"] = response_mime_type
        if response_json_schema is not None:
            kwargs["response_json_schema"] = response_json_schema
        if max_output_tokens is not None:
            kwargs["max_output_tokens"] = max_output_tokens
        if tools is not None:
            kwargs["tools"] = tools
        if thinking_level is not None:
            kwargs["thinking_config"] = types.ThinkingConfig(
                include_thoughts=include_thoughts,
                thinking_level=thinking_level,  # type: ignore[arg-type]
            )
        return types.GenerateContentConfig(**kwargs)

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
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> LLMGenerationResult:
        from google.genai import types

        base_url = self._resolve_base_url()
        if not base_url:
            raise RuntimeError(
                "AI_PROVIDER_NOT_CONFIGURED: Thiếu LLM_BASE_URL cho gateway cobhub. "
                "Hãy đặt LLM_BASE_URL trong .env (xem .env.example)."
            )
        client = self.build_google_genai_client(self._settings.llm_api_key or "", base_url)
        effective_level = _normalize_thinking_level(
            thinking_level,
            getattr(self._settings, "llm_thinking_level", "MEDIUM"),
        )
        thinking_control = self._resolve_thinking_control()
        candidate_models, degraded_set = self._resolve_candidate_models(effective_level)
        preferred_model: str | None = None
        last_requested_model: str = candidate_models[0]

        total_budget = (
            float(timeout_seconds)
            if timeout_seconds is not None and timeout_seconds > 0
            else float(getattr(self._settings, "ai_hard_timeout_seconds", 55.0))
        )
        loop = asyncio.get_running_loop()
        deadline = loop.time() + total_budget

        async def _call_model(
            contents: Any,
            config: Any,
            *,
            is_tool_turn: bool = False,
            parse_json_fn: Any | None = None,
        ) -> Any:
            nonlocal preferred_model, last_requested_model
            ordered_candidates = list(candidate_models)
            if preferred_model and preferred_model in ordered_candidates:
                ordered_candidates.remove(preferred_model)
                ordered_candidates.insert(0, preferred_model)

            http500_retries = 0
            last_err: Exception | None = None
            for cand in ordered_candidates:
                while True:
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        raise TimeoutError(
                            f"LLM call exceeded remaining timeout budget ({total_budget:.2f}s)"
                        )
                    if is_tool_turn:
                        if tool_call_timeout_seconds is not None and tool_call_timeout_seconds > 0:
                            call_timeout = min(remaining, float(tool_call_timeout_seconds))
                        else:
                            cfg_tool_timeout = float(
                                getattr(
                                    self._settings,
                                    "ai_tool_call_timeout_seconds",
                                    total_budget,
                                )
                            )
                            call_timeout = min(remaining, cfg_tool_timeout)
                    else:
                        call_timeout = remaining
                    try:
                        resp = await asyncio.wait_for(
                            client.aio.models.generate_content(
                                model=cand,
                                contents=contents,
                                config=config,
                            ),
                            timeout=call_timeout,
                        )
                        actual_model_id = (
                            str(getattr(resp, "model_version", None) or cand).strip() or cand
                        )
                        if parse_json_fn is not None:
                            parsed = parse_json_fn(resp)
                            preferred_model = cand
                            last_requested_model = cand
                            self.model_used = actual_model_id
                            self.last_model_used = actual_model_id
                            is_degraded = cand in degraded_set
                            self.degraded_model_used = is_degraded
                            self.last_degraded_model_used = is_degraded
                            return resp, parsed
                        preferred_model = cand
                        last_requested_model = cand
                        self.model_used = actual_model_id
                        self.last_model_used = actual_model_id
                        is_degraded = cand in degraded_set
                        self.degraded_model_used = is_degraded
                        self.last_degraded_model_used = is_degraded
                        return resp
                    except TimeoutError:
                        raise
                    except (json.JSONDecodeError, ValueError) as e:
                        if parse_json_fn is not None:
                            last_err = e
                            break
                        raise
                    except Exception as e:
                        err_str = str(e)
                        err_lower = err_str.lower()
                        last_err = e
                        status_code = getattr(e, "status_code", None)
                        if status_code is None and isinstance(getattr(e, "code", None), int):
                            status_code = getattr(e, "code", None)
                        is_http_500 = (
                            status_code == 500
                            or "500" in err_str
                            or "stream interrupted" in err_lower
                            or "INTERNAL" in err_str
                        )
                        if is_http_500:
                            if http500_retries < 1 and (deadline - loop.time()) > 0.1:
                                http500_retries += 1
                                await asyncio.sleep(0.05)
                                continue
                            break
                        if (
                            "503" in err_str
                            or "UNAVAILABLE" in err_str
                            or "high demand" in err_str
                            or "RESOURCE_EXHAUSTED" in err_str
                            or "429" in err_str
                            or "quota" in err_lower
                            or "404" in err_str
                            or "NOT_FOUND" in err_str
                        ):
                            break
                        raise
            if last_err is not None:
                raise last_err
            raise RuntimeError("No candidate models available for Google GenAI")

        schema_dict = _extract_json_schema(response_schema)
        tool_thinking_level = (
            ("LOW" if effective_level in ("LOW", "MEDIUM") else "MEDIUM")
            if thinking_control == "param"
            else None
        )
        final_thinking_level = effective_level if thinking_control == "param" else None
        used_tool_stage = bool(tools and tool_executor is not None and max_tool_calls > 0)

        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_thinking_tokens = 0
        tool_evidence_blocks: list[str] = []
        tool_call_records: list[LLMToolCallResultDTO] = []

        def _accumulate_usage(resp_obj: Any) -> None:
            nonlocal total_prompt_tokens, total_completion_tokens, total_thinking_tokens
            usage = getattr(resp_obj, "usage_metadata", None)
            if usage is None:
                return
            total_prompt_tokens += int(getattr(usage, "prompt_token_count", 0) or 0)
            cand_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
            thought_tokens = int(getattr(usage, "thoughts_token_count", 0) or 0)
            total_completion_tokens += cand_tokens + thought_tokens
            total_thinking_tokens += thought_tokens

        if used_tool_stage and tool_executor is not None and tools is not None:
            fn_decls = [
                types.FunctionDeclaration(
                    name=_tool_name(t),
                    description=_tool_description(t),
                    parameters_json_schema=_tool_parameters_schema(t),
                )
                for t in tools
            ]
            tool_cfg = self.build_generate_content_config(
                system_instruction=system_prompt or None,
                tools=[types.Tool(function_declarations=fn_decls)],
                thinking_level=tool_thinking_level,
            )
            contents: list[Any] = [user_prompt]
            calls_executed = 0

            while calls_executed < max_tool_calls:
                resp = await _call_model(
                    contents=contents,
                    config=tool_cfg,
                    is_tool_turn=True,
                )
                _accumulate_usage(resp)

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

        schema_enforced_by_gateway = bool(
            getattr(self._settings, "llm_schema_enforced_by_gateway", False)
        )
        compact_schema_spec = (
            render_compact_schema_spec(schema_dict)
            if (schema_dict and not schema_enforced_by_gateway)
            else ""
        )
        final_directive = (
            "[FINAL_OUTPUT_STAGE]: KHÔNG gọi thêm bất kỳ tool/function call nào ở bước này. "
            "Chỉ xuất DUY NHẤT JSON hợp lệ theo schema."
        )
        final_system_instruction = "\n\n".join(
            part for part in (system_prompt, final_directive, compact_schema_spec) if part
        )
        json_cfg = self.build_generate_content_config(
            system_instruction=final_system_instruction,
            response_mime_type="application/json",
            response_json_schema=schema_dict if schema_dict else None,
            max_output_tokens=32768,
            thinking_level=final_thinking_level,
        )

        def _parse_json_response(resp_obj: Any) -> Any:
            raw = (getattr(resp_obj, "text", None) or "").strip()
            if not raw:
                candidates_list = getattr(resp_obj, "candidates", None) or []
                finish_reason = (
                    getattr(candidates_list[0], "finish_reason", None) if candidates_list else None
                )
                raise ValueError(f"Empty JSON response from model (finish_reason={finish_reason})")
            return _parse_json_text(raw)

        final_resp, parsed = await _call_model(
            contents=final_user_prompt,
            config=json_cfg,
            is_tool_turn=False,
            parse_json_fn=_parse_json_response,
        )
        _accumulate_usage(final_resp)

        repair_attempts = 0
        try:
            validated = _normalize_schema_and_validate(parsed, response_schema)
        except (ValidationError, ValueError) as val_err:
            concise_err = format_concise_schema_errors(val_err)
            if not used_tool_stage:
                raise SchemaMismatchError(
                    f"AI_SCHEMA_VALIDATION_ERROR: {concise_err}",
                    already_repaired=False,
                    validation_summary=concise_err,
                    prompt_tokens=total_prompt_tokens,
                    output_tokens=total_completion_tokens,
                    thinking_tokens=total_thinking_tokens,
                    model_id=self.last_model_used,
                ) from val_err

            invalid_model_text = (
                getattr(final_resp, "text", None) or json.dumps(parsed, ensure_ascii=False)
            ).strip()
            contents_until_now = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=final_user_prompt)],
                )
            ]
            invalid_model_text_turn = types.Content(
                role="model",
                parts=[types.Part.from_text(text=invalid_model_text)],
            )
            repair_prompt_turn = types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=(
                            f"[SCHEMA_REPAIR_ERRORS]\n{concise_err}\n\n"
                            "Hãy sửa lại JSON ở lượt trên cho đúng hoàn toàn schema yêu cầu. "
                            "KHÔNG gọi thêm tool, chỉ xuất DUY NHẤT JSON hợp lệ."
                        )
                    )
                ],
            )
            repair_contents = [*contents_until_now, invalid_model_text_turn, repair_prompt_turn]
            repair_attempts = 1
            try:
                repair_resp, repair_parsed = await _call_model(
                    contents=repair_contents,
                    config=json_cfg,
                    is_tool_turn=False,
                    parse_json_fn=_parse_json_response,
                )
            except (json.JSONDecodeError, ValueError) as repair_parse_err:
                repair_concise = format_concise_schema_errors(repair_parse_err)
                raise SchemaMismatchError(
                    f"AI_SCHEMA_VALIDATION_ERROR: {repair_concise}",
                    already_repaired=True,
                    validation_summary=repair_concise,
                    prompt_tokens=total_prompt_tokens,
                    output_tokens=total_completion_tokens,
                    thinking_tokens=total_thinking_tokens,
                    model_id=self.last_model_used,
                ) from repair_parse_err
            _accumulate_usage(repair_resp)
            try:
                validated = _normalize_schema_and_validate(repair_parsed, response_schema)
            except (ValidationError, ValueError) as repair_val_err:
                repair_concise = format_concise_schema_errors(repair_val_err)
                raise SchemaMismatchError(
                    f"AI_SCHEMA_VALIDATION_ERROR: {repair_concise}",
                    already_repaired=True,
                    validation_summary=repair_concise,
                    prompt_tokens=total_prompt_tokens,
                    output_tokens=total_completion_tokens,
                    thinking_tokens=total_thinking_tokens,
                    model_id=self.last_model_used,
                ) from repair_val_err

        logger.info(
            "llm_generation_completed",
            requested_model=last_requested_model,
            actual_model_id=self.last_model_used,
            prompt_tokens=total_prompt_tokens,
            output_tokens=total_completion_tokens,
            thinking_tokens=total_thinking_tokens,
            repair_attempts=repair_attempts,
        )
        return LLMGenerationResult(
            payload=validated,
            prompt_tokens=total_prompt_tokens,
            output_tokens=total_completion_tokens,
            thinking_tokens=total_thinking_tokens,
            model_id=self.last_model_used,
            raw_tool_results=tuple(tool_call_records),
            repair_attempts=repair_attempts,
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
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
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
                timeout_seconds=timeout_seconds,
                tool_call_timeout_seconds=tool_call_timeout_seconds,
            )

        from litellm import acompletion

        total_budget = (
            float(timeout_seconds)
            if timeout_seconds is not None and timeout_seconds > 0
            else float(getattr(self._settings, "ai_hard_timeout_seconds", 55.0))
        )
        schema_dict = _extract_json_schema(response_schema)
        schema_enforced_by_gateway = bool(
            getattr(self._settings, "llm_schema_enforced_by_gateway", False)
        )
        compact_spec = (
            render_compact_schema_spec(schema_dict)
            if (schema_dict and not schema_enforced_by_gateway)
            else ""
        )
        sys_content = (
            f"{system_prompt}\n\n{compact_spec}".strip() if compact_spec else system_prompt
        )

        response = await asyncio.wait_for(
            acompletion(
                model=self.model_identifier,
                messages=[
                    {"role": "system", "content": sys_content},
                    {"role": "user", "content": user_prompt},
                ],
                api_key=self._settings.llm_api_key,
                api_base=self._resolve_base_url(),
                response_format={"type": "json_object"},
                timeout=total_budget,
            ),
            timeout=total_budget,
        )
        content = (response.choices[0].message.content or "{}").strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE).strip()
        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        details = getattr(usage, "completion_tokens_details", None)
        thinking_tokens = int(getattr(details, "reasoning_tokens", 0) or 0)
        completion_tokens = max(completion_tokens, thinking_tokens)
        parsed = json.loads(content)
        actual_model_id = (
            str(getattr(response, "model", None) or self.model_identifier).split("/")[-1].strip()
            or self.model_identifier.split("/")[-1]
        )
        self.model_used = actual_model_id
        self.last_model_used = actual_model_id
        try:
            validated_dict = _normalize_schema_and_validate(parsed, response_schema)
        except (ValidationError, ValueError) as val_err:
            concise_err = format_concise_schema_errors(val_err)
            raise SchemaMismatchError(
                f"AI_SCHEMA_VALIDATION_ERROR: {concise_err}",
                already_repaired=False,
                validation_summary=concise_err,
                prompt_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                thinking_tokens=thinking_tokens,
                model_id=self.last_model_used,
            ) from val_err
        logger.info(
            "llm_generation_completed",
            requested_model=self.model_identifier,
            actual_model_id=actual_model_id,
            prompt_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            thinking_tokens=thinking_tokens,
            repair_attempts=0,
        )
        return LLMGenerationResult(
            payload=validated_dict,
            prompt_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            thinking_tokens=thinking_tokens,
            model_id=self.last_model_used,
        )

    @staticmethod
    async def probe_cobhub_capabilities(
        settings: Any | None = None,
        *,
        force: bool = False,
        timeout_seconds: float = _DEFAULT_PROBE_TIMEOUT_SECONDS,
    ) -> CobhubCapabilityProbeResult:
        """Probe cobhub gateway schema enforcement & low-thinking behavior (cached)."""
        return await probe_cobhub_capabilities(
            settings,
            force=force,
            timeout_seconds=timeout_seconds,
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


async def probe_cobhub_capabilities(
    settings: Any | None = None,
    *,
    force: bool = False,
    timeout_seconds: float = _DEFAULT_PROBE_TIMEOUT_SECONDS,
) -> CobhubCapabilityProbeResult:
    """Probe cobhub gateway schema enforcement & low-thinking model behavior with caching."""
    effective_settings = settings if settings is not None else get_settings()
    provider = str(getattr(effective_settings, "llm_provider", "") or "").strip().lower()
    resolved_base_url = _rewrite_docker_localhost(getattr(effective_settings, "llm_base_url", ""))
    default_model = (
        str(getattr(effective_settings, "llm_model", "") or "gemini-3.8-flash-medium")
        .split("/")[-1]
        .strip()
        or "gemini-3.8-flash-medium"
    )
    low_model = (
        str(getattr(effective_settings, "llm_model_low", "") or default_model)
        .split("/")[-1]
        .strip()
        or default_model
    )
    configured_schema_enforced = bool(
        getattr(effective_settings, "llm_schema_enforced_by_gateway", False)
    )

    if provider != "gemini" or not resolved_base_url:
        return CobhubCapabilityProbeResult(
            base_url=resolved_base_url or "",
            requested_low_model=low_model,
            actual_model_id="",
            schema_enforced_detected=configured_schema_enforced,
            low_model_thinking_tokens=0,
            low_thinking_is_low=True,
            configured_schema_enforced=configured_schema_enforced,
            probe_succeeded=False,
            error="AI_PROVIDER_NOT_CONFIGURED",
            cached=False,
        )

    cache_key = (resolved_base_url, low_model)
    if not force and cache_key in _COBHUB_PROBE_CACHE:
        return replace(_COBHUB_PROBE_CACHE[cache_key], cached=True)

    try:
        client = LiteLLMAdapter.build_google_genai_client(
            str(getattr(effective_settings, "llm_api_key", "") or ""),
            resolved_base_url,
        )
        loop = asyncio.get_running_loop()
        deadline = loop.time() + max(0.5, float(timeout_seconds))

        # Probe 1: send minimal JSON request with response_json_schema only (no system schema injection).
        probe1_cfg = LiteLLMAdapter.build_generate_content_config(
            system_instruction="You are a minimal JSON health probe.",
            response_mime_type="application/json",
            response_json_schema=_GatewaySchemaProbeModel.model_json_schema(),
            max_output_tokens=128,
            thinking_level=None,
        )
        rem1 = max(0.1, deadline - loop.time())
        resp1 = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=low_model,
                contents="Return a valid JSON object.",
                config=probe1_cfg,
            ),
            timeout=rem1,
        )
        schema_enforced_detected = False
        raw_text1 = (getattr(resp1, "text", None) or "").strip()
        if raw_text1:
            try:
                parsed1 = _parse_json_text(raw_text1)
                _GatewaySchemaProbeModel.model_validate(parsed1)
                schema_enforced_detected = True
            except (json.JSONDecodeError, ValidationError, ValueError):
                schema_enforced_detected = False

        # Probe 2: call configured llm_model_low and inspect actual_model_id + thoughts_token_count.
        thinking_control = (
            str(
                getattr(effective_settings, "llm_thinking_control", "model_suffix")
                or "model_suffix"
            )
            .strip()
            .lower()
        )
        probe2_thinking_level = "LOW" if thinking_control == "param" else None
        probe2_cfg = LiteLLMAdapter.build_generate_content_config(
            system_instruction="Return minimal JSON.",
            response_mime_type="application/json",
            max_output_tokens=128,
            thinking_level=probe2_thinking_level,
        )
        rem2 = deadline - loop.time()
        if rem2 <= 0:
            raise TimeoutError(f"Cobhub capability probe exceeded timeout ({timeout_seconds:.1f}s)")
        resp2 = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=low_model,
                contents='Trả về JSON {"ok": true}.',
                config=probe2_cfg,
            ),
            timeout=rem2,
        )
        actual_model_id = (
            str(getattr(resp2, "model_version", None) or low_model).strip() or low_model
        )
        usage2 = getattr(resp2, "usage_metadata", None)
        low_thinking_tokens = int(getattr(usage2, "thoughts_token_count", 0) or 0)
        low_thinking_is_low = low_thinking_tokens <= _LOW_THINKING_MAX_TOKENS

        mismatches: list[str] = []
        if schema_enforced_detected != configured_schema_enforced:
            mismatches.append("schema_enforced_mismatch")
        if not low_thinking_is_low:
            mismatches.append("low_thinking_tokens_exceeded")
        if low_model not in actual_model_id and actual_model_id != low_model:
            mismatches.append("low_model_id_mismatch")

        result = CobhubCapabilityProbeResult(
            base_url=resolved_base_url,
            requested_low_model=low_model,
            actual_model_id=actual_model_id,
            schema_enforced_detected=schema_enforced_detected,
            low_model_thinking_tokens=low_thinking_tokens,
            low_thinking_is_low=low_thinking_is_low,
            configured_schema_enforced=configured_schema_enforced,
            mismatches=tuple(mismatches),
            probe_succeeded=True,
            error=None,
            cached=False,
        )
        _COBHUB_PROBE_CACHE[cache_key] = result
        if mismatches:
            logger.warning(
                "cobhub_capability_mismatch",
                base_url=resolved_base_url,
                requested_low_model=low_model,
                actual_model_id=actual_model_id,
                schema_enforced_detected=schema_enforced_detected,
                configured_schema_enforced=configured_schema_enforced,
                low_model_thinking_tokens=low_thinking_tokens,
                low_thinking_is_low=low_thinking_is_low,
                mismatches=mismatches,
            )
        else:
            logger.info(
                "cobhub_capability_probe_completed",
                base_url=resolved_base_url,
                requested_low_model=low_model,
                actual_model_id=actual_model_id,
                schema_enforced_detected=schema_enforced_detected,
                low_model_thinking_tokens=low_thinking_tokens,
                low_thinking_is_low=low_thinking_is_low,
            )
        return result
    except Exception as exc:
        safe_err = f"{type(exc).__name__}: {str(exc)[:200]}"
        logger.warning(
            "cobhub_capability_probe_failed",
            base_url=resolved_base_url,
            requested_low_model=low_model,
            error=safe_err,
        )
        return CobhubCapabilityProbeResult(
            base_url=resolved_base_url,
            requested_low_model=low_model,
            actual_model_id="",
            schema_enforced_detected=configured_schema_enforced,
            low_model_thinking_tokens=0,
            low_thinking_is_low=True,
            configured_schema_enforced=configured_schema_enforced,
            mismatches=(),
            probe_succeeded=False,
            error=safe_err,
            cached=False,
        )
