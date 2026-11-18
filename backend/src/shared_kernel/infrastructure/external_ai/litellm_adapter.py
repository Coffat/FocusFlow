import asyncio
import hashlib
import json
import os
import re
import threading
import time
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal
from weakref import WeakKeyDictionary, ref

import httpx
import structlog
from pydantic import BaseModel, ValidationError

from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMProviderPort,
    LLMToolCallResultDTO,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
    SchemaMismatchError,
    extract_upstream_model_from_response,
    format_concise_schema_errors,
)
from src.shared_kernel.config import get_settings

_REAL_HTTPX_ASYNC_CLIENT_CLS = httpx.AsyncClient

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
    gateway_models: tuple[str, ...] = ()
    checked_configured_models: dict[str, str] = field(default_factory=dict)
    missing_gateway_models: tuple[str, ...] = ()
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
            "gateway_models": list(self.gateway_models),
            "checked_configured_models": dict(self.checked_configured_models),
            "missing_gateway_models": list(self.missing_gateway_models),
            "error": self.error,
            "cached": self.cached,
        }


_COBHUB_PROBE_CACHE: dict[
    tuple[str, str, tuple[tuple[str, str], ...]], CobhubCapabilityProbeResult
] = {}
_GENAI_CLIENT_CACHE_LOCK = threading.Lock()
_GENAI_CLIENT_CACHE: dict[tuple[str, str, str], tuple[Any, Any]] = {}
_GENAI_CLIENT_LOOPS: dict[tuple[str, str, str], ref[asyncio.AbstractEventLoop] | None] = {}
_GENAI_HTTPX_CLIENTS: dict[tuple[str, str, str], httpx.AsyncClient] = {}
_OUTBOUND_SEMAPHORES_LOCK = threading.Lock()
_OUTBOUND_SEMAPHORES: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = (
    WeakKeyDictionary()
)
_OUTBOUND_SEMAPHORE_LIMITS: WeakKeyDictionary[asyncio.AbstractEventLoop, int] = WeakKeyDictionary()


def _extract_httpx_async_client(client: Any) -> httpx.AsyncClient | None:
    api_client = getattr(client, "_api_client", None)
    http_opts = getattr(api_client, "_http_options", None)
    hc = getattr(http_opts, "httpx_async_client", None)
    if isinstance(hc, _REAL_HTTPX_ASYNC_CLIENT_CLS):
        return hc
    fake_kwargs = getattr(client, "kwargs", None)
    if isinstance(fake_kwargs, dict):
        hc_fake = getattr(fake_kwargs.get("http_options"), "httpx_async_client", None)
        if isinstance(hc_fake, _REAL_HTTPX_ASYNC_CLIENT_CLS):
            return hc_fake
    return None


def clear_google_genai_client_cache() -> None:
    """Clear cached google-genai Client instances and close bound httpx pools when safe."""
    try:
        running_loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    with _GENAI_CLIENT_CACHE_LOCK:
        _GENAI_CLIENT_CACHE.clear()
        loops_snapshot = dict(_GENAI_CLIENT_LOOPS)
        clients_snapshot = dict(_GENAI_HTTPX_CLIENTS)
        _GENAI_CLIENT_LOOPS.clear()
        _GENAI_HTTPX_CLIENTS.clear()

    for key, hc in clients_snapshot.items():
        if hc.is_closed:
            continue
        loop_ref = loops_snapshot.get(key)
        bound_loop = loop_ref() if loop_ref is not None else None
        if (
            running_loop is not None
            and not running_loop.is_closed()
            and (bound_loop is None or bound_loop is running_loop)
        ):
            running_loop.create_task(hc.aclose())


async def aclose_google_genai_clients() -> None:
    """Async cleanup helper closing all cached httpx.AsyncClient pools."""
    with _GENAI_CLIENT_CACHE_LOCK:
        _GENAI_CLIENT_CACHE.clear()
        _GENAI_CLIENT_LOOPS.clear()
        clients = list(_GENAI_HTTPX_CLIENTS.values())
        _GENAI_HTTPX_CLIENTS.clear()

    for hc in clients:
        if not hc.is_closed:
            try:
                await hc.aclose()
            except Exception:
                pass


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


def _normalize_thinking_level(raw_level: str | None) -> str:
    level = (raw_level or "").strip().upper()
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
        provider = (self._settings.llm_provider or "").strip().lower()
        model = (getattr(self._settings, "llm_model", "") or "").strip()
        if not model:
            if (
                not self._should_use_google_genai_sdk()
                or self._resolve_thinking_control() == "param"
            ):
                raise RuntimeError(
                    "AI_PROVIDER_NOT_CONFIGURED: Missing LLM_MODEL for configured provider."
                )
            for tier_attr in ("llm_model_medium", "llm_model_low", "llm_model_high"):
                candidate = (getattr(self._settings, tier_attr, "") or "").strip()
                if candidate:
                    model = candidate
                    break
            if not model:
                raise RuntimeError(
                    "AI_PROVIDER_NOT_CONFIGURED: Missing LLM_MODEL for configured provider."
                )
        if "/" in model:
            return model
        return f"{provider}/{model}"

    def _should_use_google_genai_sdk(self) -> bool:
        return self._settings.llm_provider.strip().lower() == "gemini"

    def _resolve_base_url(self) -> str | None:
        return _rewrite_docker_localhost(getattr(self._settings, "llm_base_url", ""))

    def _resolve_thinking_control(self) -> str:
        return _normalize_thinking_control(self._settings)

    def _resolve_candidate_models(self, thinking_level: str | None) -> tuple[list[str], set[str]]:
        effective_level = _normalize_thinking_level(thinking_level)
        if self._resolve_thinking_control() == "param":
            default_model = (
                str(getattr(self._settings, "llm_model", "") or "").split("/")[-1].strip()
            )
            if not default_model:
                raise RuntimeError(
                    "AI_PROVIDER_NOT_CONFIGURED: Missing LLM_MODEL for thinking_control='param'."
                )
            candidates = [default_model]
        else:
            tier_attr = {
                "LOW": "llm_model_low",
                "MEDIUM": "llm_model_medium",
                "HIGH": "llm_model_high",
            }[effective_level]
            env_var_name = tier_attr.upper()
            if not hasattr(self._settings, tier_attr):
                raise RuntimeError(
                    f"AI_PROVIDER_NOT_CONFIGURED: Missing {env_var_name} for thinking_level={effective_level}."
                )
            raw_tier_model = getattr(self._settings, tier_attr, "") or ""
            tier_model = str(raw_tier_model).split("/")[-1].strip()
            if not tier_model:
                raise RuntimeError(
                    f"AI_PROVIDER_NOT_CONFIGURED: Blank {env_var_name} for thinking_level={effective_level}."
                )
            candidates = [tier_model]

        raw_fallbacks = str(getattr(self._settings, "llm_fallback_models", "") or "")
        for raw_item in raw_fallbacks.split(","):
            fallback_model = raw_item.strip().split("/")[-1].strip()
            if fallback_model and fallback_model not in candidates:
                candidates.append(fallback_model)

        return candidates, set()

    def resolve_model_for_thinking_level(self, thinking_level: str | None) -> str:
        """Resolve the primary configured model for the given thinking level."""
        if not self._should_use_google_genai_sdk():
            return self.model_identifier
        candidates, _ = self._resolve_candidate_models(thinking_level)
        return candidates[0] if candidates else self.model_identifier

    @staticmethod
    def build_google_genai_client(api_key: str, base_url: str) -> Any:
        """Build a google-genai Client configured for the cobhub proxy endpoint."""
        from google import genai
        from google.genai import types

        httpx_async_client = _REAL_HTTPX_ASYNC_CLIENT_CLS(
            limits=httpx.Limits(
                max_connections=12,
                max_keepalive_connections=6,
                keepalive_expiry=30.0,
            ),
            http2=False,
        )
        http_opts = types.HttpOptions(
            base_url=base_url,
            api_version="v1beta",
            retry_options=types.HttpRetryOptions(attempts=1),
            httpx_async_client=httpx_async_client,
        )
        effective_key = (api_key or "").strip() or "antigravity-proxy-key"
        return genai.Client(
            api_key=effective_key,
            http_options=http_opts,
        )

    @classmethod
    def get_shared_google_genai_client(cls, api_key: str, base_url: str) -> Any:
        """Return a cached google-genai Client keyed by (base_url, sha256(api_key), loop_tag)."""
        from google import genai

        normalized_url = (base_url or "").strip()
        effective_key = (api_key or "").strip() or "antigravity-proxy-key"
        key_digest = hashlib.sha256(effective_key.encode("utf-8")).hexdigest()
        try:
            running_loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
            loop_tag = f"loop:{id(running_loop)}"
        except RuntimeError:
            running_loop = None
            loop_tag = "loop:none"
        cache_key = (normalized_url, key_digest, loop_tag)
        current_client_cls = genai.Client

        with _GENAI_CLIENT_CACHE_LOCK:
            # Prune entries bound to closed or garbage-collected event loops
            stale_keys = [
                k
                for k, loop_ref in _GENAI_CLIENT_LOOPS.items()
                if loop_ref is not None and (loop_ref() is None or loop_ref().is_closed())  # type: ignore[union-attr]
            ]
            for sk in stale_keys:
                _GENAI_CLIENT_CACHE.pop(sk, None)
                _GENAI_CLIENT_LOOPS.pop(sk, None)
                _GENAI_HTTPX_CLIENTS.pop(sk, None)

            cached_entry = _GENAI_CLIENT_CACHE.get(cache_key)
            cached_loop_ref = _GENAI_CLIENT_LOOPS.get(cache_key)
            cached_httpx = _GENAI_HTTPX_CLIENTS.get(cache_key)
            loop_matches = running_loop is None or (
                cached_loop_ref is not None
                and cached_loop_ref() is running_loop
                and not running_loop.is_closed()
            )
            httpx_alive = cached_httpx is None or not cached_httpx.is_closed
            if (
                cached_entry is not None
                and cached_entry[0] is current_client_cls
                and loop_matches
                and httpx_alive
            ):
                return cached_entry[1]

            client = cls.build_google_genai_client(api_key, normalized_url)
            _GENAI_CLIENT_CACHE[cache_key] = (current_client_cls, client)
            _GENAI_CLIENT_LOOPS[cache_key] = ref(running_loop) if running_loop is not None else None
            hc = _extract_httpx_async_client(client)
            if hc is not None:
                _GENAI_HTTPX_CLIENTS[cache_key] = hc
            return client

    def _get_outbound_semaphore(self, loop: asyncio.AbstractEventLoop) -> asyncio.Semaphore:
        """Return per-loop bounded outbound semaphore sized by ai_max_concurrent_llm_requests."""
        raw_limit = getattr(self._settings, "ai_max_concurrent_llm_requests", 4)
        limit = max(1, int(raw_limit if raw_limit is not None else 4))
        with _OUTBOUND_SEMAPHORES_LOCK:
            existing = _OUTBOUND_SEMAPHORES.get(loop)
            existing_limit = _OUTBOUND_SEMAPHORE_LIMITS.get(loop)
            if existing is not None and existing_limit == limit:
                return existing
            sem = asyncio.Semaphore(limit)
            _OUTBOUND_SEMAPHORES[loop] = sem
            _OUTBOUND_SEMAPHORE_LIMITS[loop] = limit
            return sem

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

        kwargs: dict[str, Any] = {
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
        }
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
        client = self.get_shared_google_genai_client(self._settings.llm_api_key or "", base_url)
        effective_level = _normalize_thinking_level(thinking_level)
        thinking_control = self._resolve_thinking_control()
        candidate_models, degraded_set = self._resolve_candidate_models(effective_level)
        preferred_model: str | None = None
        last_requested_model: str = candidate_models[0]

        t_start_total = time.perf_counter()
        total_queue_wait_ms: float = 0.0
        total_connect_ms: float = 0.0
        total_ttft_ms: float = 0.0
        total_generation_ms: float = 0.0
        total_retries: int = 0

        total_budget = (
            float(timeout_seconds)
            if timeout_seconds is not None and timeout_seconds > 0
            else float(getattr(self._settings, "ai_hard_timeout_seconds", 55.0))
        )
        loop = asyncio.get_running_loop()
        deadline = loop.time() + total_budget
        outbound_semaphore = self._get_outbound_semaphore(loop)

        async def _call_model(
            contents: Any,
            config: Any,
            *,
            is_tool_turn: bool = False,
            parse_json_fn: Any | None = None,
        ) -> Any:
            nonlocal \
                preferred_model, \
                last_requested_model, \
                total_queue_wait_ms, \
                total_connect_ms, \
                total_ttft_ms, \
                total_generation_ms, \
                total_retries
            ordered_candidates = list(candidate_models)
            if preferred_model and preferred_model in ordered_candidates:
                ordered_candidates.remove(preferred_model)
                ordered_candidates.insert(0, preferred_model)

            http500_retries = 0
            last_err: Exception | None = None
            for cand in ordered_candidates:
                while True:
                    remaining_wait = deadline - loop.time()
                    if remaining_wait <= 0:
                        raise TimeoutError(
                            f"LLM call exceeded remaining timeout budget ({total_budget:.2f}s)"
                        )
                    t_sem_start = time.perf_counter()
                    try:
                        async with asyncio.timeout(remaining_wait):
                            await outbound_semaphore.acquire()
                    except TimeoutError as sem_exc:
                        raise TimeoutError(
                            f"LLM call exceeded remaining timeout budget ({total_budget:.2f}s)"
                        ) from sem_exc
                    sem_wait = (time.perf_counter() - t_sem_start) * 1000.0
                    total_queue_wait_ms += sem_wait

                    t_conn_start = time.perf_counter()
                    _ = getattr(client, "aio", None)
                    t_conn_end = time.perf_counter()
                    conn_wait = (t_conn_end - t_conn_start) * 1000.0
                    total_connect_ms += conn_wait

                    try:
                        remaining = deadline - loop.time()
                        if remaining <= 0:
                            raise TimeoutError(
                                f"LLM call exceeded remaining timeout budget ({total_budget:.2f}s)"
                            )
                        if is_tool_turn:
                            if (
                                tool_call_timeout_seconds is not None
                                and tool_call_timeout_seconds > 0
                            ):
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

                        t_req_start = time.perf_counter()
                        resp = await asyncio.wait_for(
                            client.aio.models.generate_content(
                                model=cand,
                                contents=contents,
                                config=config,
                            ),
                            timeout=call_timeout,
                        )
                        t_req_end = time.perf_counter()
                        req_elapsed_ms = (t_req_end - t_req_start) * 1000.0

                        raw_ttft = getattr(resp, "provider_ttft_ms", getattr(resp, "ttft_ms", None))
                        raw_gen = getattr(resp, "generation_ms", None)
                        raw_conn = getattr(resp, "connect_ms", None)
                        raw_queue = getattr(resp, "queue_wait_ms", None)
                        if raw_queue is not None:
                            total_queue_wait_ms += float(raw_queue) - sem_wait
                        if raw_conn is not None:
                            total_connect_ms += float(raw_conn) - conn_wait

                        ttft_val = float(raw_ttft) if raw_ttft is not None else req_elapsed_ms
                        gen_val = (
                            float(raw_gen)
                            if raw_gen is not None
                            else (
                                max(0.0, req_elapsed_ms - ttft_val) if raw_ttft is not None else 0.0
                            )
                        )
                        total_ttft_ms += ttft_val
                        total_generation_ms += gen_val
                    except TimeoutError:
                        raise
                    except (json.JSONDecodeError, ValueError) as e:
                        if parse_json_fn is not None:
                            last_err = e
                            total_retries += 1
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
                                total_retries += 1
                                await asyncio.sleep(0.05)
                                continue
                            total_retries += 1
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
                            total_retries += 1
                            break
                        raise
                    finally:
                        outbound_semaphore.release()

                    verified_m, fallback_m = extract_upstream_model_from_response(
                        resp, default_model=cand
                    )
                    actual_model_id = verified_m or fallback_m
                    if parse_json_fn is not None:
                        t_parse_start = time.perf_counter()
                        try:
                            parsed = parse_json_fn(resp)
                        except (json.JSONDecodeError, ValueError) as e:
                            last_err = e
                            total_retries += 1
                            break
                        t_parse_end = time.perf_counter()
                        if raw_gen is None and raw_ttft is None:
                            total_generation_ms += (t_parse_end - t_parse_start) * 1000.0
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
            p_tok = int(getattr(usage, "prompt_token_count", 0) or 0)
            total_prompt_tokens += p_tok
            tot_tok = getattr(usage, "total_token_count", None)
            thought_tokens = int(getattr(usage, "thoughts_token_count", 0) or 0)
            if tot_tok is not None and int(tot_tok) > 0:
                # Provider semantic: total_token_count = prompt_tokens + billable_output_tokens
                # When candidates_token_count and thoughts_token_count are both reported,
                # max(0, tot_tok - p_tok) guarantees thinking tokens are included exactly once
                total_completion_tokens += max(0, int(tot_tok) - p_tok)
            else:
                cand_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
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

        total_elapsed_ms = (time.perf_counter() - t_start_total) * 1000.0
        latency_breakdown = {
            "queue_wait_ms": round(total_queue_wait_ms, 2),
            "connect_ms": round(total_connect_ms, 2),
            "provider_ttft_ms": round(total_ttft_ms, 2),
            "ttft_ms": round(total_ttft_ms, 2),
            "generation_ms": round(total_generation_ms, 2),
            "total_elapsed_ms": round(total_elapsed_ms, 2),
            "retries": total_retries,
        }

        logger.debug(
            "llm_latency_telemetry",
            queue_wait_ms=round(total_queue_wait_ms, 2),
            connect_ms=round(total_connect_ms, 2),
            ttft_ms=round(total_ttft_ms, 2),
            generation_ms=round(total_generation_ms, 2),
            total_elapsed_ms=round(total_elapsed_ms, 2),
            model_id=self.last_model_used,
            retries=total_retries,
        )
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
            latency_metrics=latency_breakdown,
            retries=total_retries,
            resolved_model=self.last_model_used,
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


def _normalize_thinking_control(effective_settings: Any) -> str:
    raw = str(getattr(effective_settings, "llm_thinking_control", "model_suffix") or "model_suffix")
    mode = raw.strip().lower()
    return mode if mode in {"model_suffix", "param"} else "model_suffix"


def _collect_configured_models(effective_settings: Any) -> dict[str, str]:
    configured: dict[str, str] = {}
    provider = str(getattr(effective_settings, "llm_provider", "") or "").strip().lower()
    thinking_control = _normalize_thinking_control(effective_settings)
    if provider == "gemini" and thinking_control == "model_suffix":
        target_fields: tuple[str, ...] = ("llm_model_low", "llm_model_medium", "llm_model_high")
    else:
        target_fields = ("llm_model",)

    for field_name in target_fields:
        raw_val = str(getattr(effective_settings, field_name, "") or "").strip()
        model_id = raw_val.split("/")[-1].strip() if raw_val else ""
        if model_id:
            configured[field_name] = model_id
    raw_fallbacks = str(getattr(effective_settings, "llm_fallback_models", "") or "")
    fallback_idx = 0
    for raw_item in raw_fallbacks.split(","):
        fb_id = raw_item.strip().split("/")[-1].strip()
        if fb_id:
            configured[f"llm_fallback_models[{fallback_idx}]"] = fb_id
            fallback_idx += 1
    return configured


async def _fetch_gateway_v1beta_models(
    base_url: str,
    api_key: str,
    timeout_seconds: float,
) -> tuple[str, ...]:
    cleaned_base = base_url.rstrip("/")
    models_url = (
        f"{cleaned_base}/models"
        if cleaned_base.endswith("/v1beta")
        else f"{cleaned_base}/v1beta/models"
    )
    headers: dict[str, str] = {}
    cleaned_key = (api_key or "").strip()
    if cleaned_key:
        headers["x-goog-api-key"] = cleaned_key
        headers["Authorization"] = f"Bearer {cleaned_key}"
    async with httpx.AsyncClient(timeout=max(0.1, float(timeout_seconds))) as http_client:
        response = await http_client.get(models_url, headers=headers)
        response.raise_for_status()
        payload = response.json()
    raw_models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(raw_models, list):
        return ()
    parsed_models: list[str] = []
    for item in raw_models:
        if isinstance(item, dict):
            raw_name = str(item.get("name") or "").strip()
        elif isinstance(item, str):
            raw_name = item.strip()
        else:
            continue
        normalized = raw_name.removeprefix("models/").strip()
        if normalized and normalized not in parsed_models:
            parsed_models.append(normalized)
    return tuple(parsed_models)


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
    thinking_control = _normalize_thinking_control(effective_settings)
    checked_configured_models = _collect_configured_models(effective_settings)
    if thinking_control == "param":
        low_model = checked_configured_models.get("llm_model") or ""
    else:
        low_model = checked_configured_models.get("llm_model_low") or ""
    configured_schema_enforced = bool(
        getattr(effective_settings, "llm_schema_enforced_by_gateway", False)
    )

    if provider != "gemini" or not resolved_base_url or not low_model:
        return CobhubCapabilityProbeResult(
            base_url=resolved_base_url or "",
            requested_low_model=low_model,
            actual_model_id="",
            schema_enforced_detected=configured_schema_enforced,
            low_model_thinking_tokens=0,
            low_thinking_is_low=True,
            configured_schema_enforced=configured_schema_enforced,
            checked_configured_models=checked_configured_models,
            probe_succeeded=False,
            error="AI_PROVIDER_NOT_CONFIGURED",
            cached=False,
        )

    cache_key = (
        resolved_base_url,
        low_model,
        tuple(sorted(checked_configured_models.items())),
    )
    if not force and cache_key in _COBHUB_PROBE_CACHE:
        return replace(_COBHUB_PROBE_CACHE[cache_key], cached=True)

    try:
        api_key = str(getattr(effective_settings, "llm_api_key", "") or "")
        client = LiteLLMAdapter.get_shared_google_genai_client(
            api_key,
            resolved_base_url,
        )
        loop = asyncio.get_running_loop()
        deadline = loop.time() + max(0.5, float(timeout_seconds))

        gateway_models: tuple[str, ...] = ()
        missing_gateway_models: tuple[str, ...] = ()
        models_list_fetched = False
        rem_models = max(0.1, deadline - loop.time())
        try:
            gateway_models = await asyncio.wait_for(
                _fetch_gateway_v1beta_models(
                    resolved_base_url,
                    api_key,
                    rem_models,
                ),
                timeout=rem_models,
            )
            models_list_fetched = True
        except Exception as models_exc:
            logger.warning(
                "cobhub_models_list_probe_failed",
                base_url=resolved_base_url,
                error=f"{type(models_exc).__name__}: {str(models_exc)[:200]}",
            )

        if models_list_fetched:
            gateway_set = set(gateway_models)
            missing_list: list[str] = []
            for model_id in checked_configured_models.values():
                if model_id not in gateway_set and model_id not in missing_list:
                    missing_list.append(model_id)
            missing_gateway_models = tuple(missing_list)

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

        # Probe 2: call configured low-thinking target model and inspect actual_model_id + thoughts_token_count.
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
        if missing_gateway_models:
            mismatches.append("configured_models_missing_from_gateway")

        result = CobhubCapabilityProbeResult(
            base_url=resolved_base_url,
            requested_low_model=low_model,
            actual_model_id=actual_model_id,
            schema_enforced_detected=schema_enforced_detected,
            low_model_thinking_tokens=low_thinking_tokens,
            low_thinking_is_low=low_thinking_is_low,
            configured_schema_enforced=configured_schema_enforced,
            mismatches=tuple(mismatches),
            gateway_models=gateway_models,
            checked_configured_models=checked_configured_models,
            missing_gateway_models=missing_gateway_models,
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
                checked_configured_models=checked_configured_models,
                missing_gateway_models=list(missing_gateway_models),
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
                gateway_models_count=len(gateway_models),
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
            checked_configured_models=checked_configured_models,
            probe_succeeded=False,
            error=safe_err,
            cached=False,
        )
