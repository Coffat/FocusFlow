"""Shared utilities for Group 0 cobhub & embedding baseline experiments.

Never logs, prints, or persists API keys or PII.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
EXPERIMENTS_OUT_DIR = REPO_ROOT / "docs" / "experiments"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import dotenv_values  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from src.evaluation.application.prompts import build_evaluation_prompt_registry  # noqa: E402
from src.planning.application.services.roadmap_skills import (  # noqa: E402
    build_planning_prompt_registry,
)
from src.shared_kernel.application.harness.models import PromptTemplate  # noqa: E402
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import (  # noqa: E402
    LiteLLMAdapter,
)

_SECRET_PATTERN = re.compile(
    r"(AIza[0-9A-Za-z\-_]{20,}|sk-[0-9A-Za-z\-_]{16,}|Bearer\s+[0-9A-Za-z\-_.]{12,})",
    re.IGNORECASE,
)


def _merged_dotenv() -> dict[str, str]:
    merged: dict[str, str] = {}
    for candidate in (REPO_ROOT / ".env", BACKEND_DIR / ".env"):
        if candidate.exists():
            raw = dotenv_values(candidate)
            for k, v in raw.items():
                if v is not None and str(v).strip():
                    merged[str(k)] = str(v).strip()
    return merged


def get_cobhub_config() -> tuple[str, str]:
    """Return `(base_url, llm_api_key)` for cobhub experiments.

    Requires explicit `LLM_BASE_URL` env var; reads `LLM_API_KEY` from env or `.env`
    without falling back to `GEMINI_API_KEY`.
    """
    base_url = (os.getenv("LLM_BASE_URL") or "").strip()
    if not base_url:
        raise RuntimeError(
            "Missing LLM_BASE_URL environment variable. "
            "Pass LLM_BASE_URL=http://127.0.0.1:8045 explicitly."
        )
    env_key = (os.getenv("LLM_API_KEY") or os.getenv("LLM_KEY") or "").strip()
    if not env_key:
        dotenv_map = _merged_dotenv()
        env_key = (dotenv_map.get("LLM_API_KEY") or dotenv_map.get("LLM_KEY") or "").strip()
    if not env_key:
        raise RuntimeError("Missing LLM_API_KEY in environment or .env.")
    return base_url, env_key


def get_embedding_studio_api_key() -> tuple[str, str]:
    """Return `(api_key, source_name)` from `EMBEDDING_API_KEY` or `GEMINI_API_KEY` only."""
    dotenv_map = _merged_dotenv()
    for name in ("EMBEDDING_API_KEY", "GEMINI_API_KEY"):
        val = (os.getenv(name) or dotenv_map.get(name) or "").strip()
        if val:
            return val, name
    raise RuntimeError(
        "Missing EMBEDDING_API_KEY or GEMINI_API_KEY in environment or .env "
        "(refusing to fall back to LLM_API_KEY)."
    )


def build_cobhub_client() -> Any:
    """Build google-genai client reusing `LiteLLMAdapter.build_google_genai_client`."""
    base_url, api_key = get_cobhub_config()
    return LiteLLMAdapter.build_google_genai_client(api_key=api_key, base_url=base_url)


def build_genai_config(
    *,
    system_instruction: str | None = None,
    response_mime_type: str | None = None,
    response_json_schema: dict[str, Any] | None = None,
    max_output_tokens: int | None = None,
    thinking_level: str | None = None,
    tools: list[Any] | None = None,
    include_thoughts: bool = False,
) -> Any:
    """Build GenerateContentConfig reusing `LiteLLMAdapter.build_generate_content_config`."""
    return LiteLLMAdapter.build_generate_content_config(
        system_instruction=system_instruction,
        response_mime_type=response_mime_type,
        response_json_schema=response_json_schema,
        max_output_tokens=max_output_tokens,
        thinking_level=thinking_level,
        tools=tools,
        include_thoughts=include_thoughts,
    )


def get_prompt_template(prompt_id: str) -> PromptTemplate:
    """Fetch a real versioned prompt from planning or evaluation PromptRegistry."""
    planning_reg = build_planning_prompt_registry()
    try:
        return planning_reg.latest(prompt_id)
    except KeyError:
        eval_reg = build_evaluation_prompt_registry()
        return eval_reg.latest(prompt_id)


def sanitize_error_message(exc: BaseException) -> str:
    msg = f"{type(exc).__name__}: {exc}"
    return _SECRET_PATTERN.sub("[REDACTED_SECRET]", msg)[:500]


def extract_response_telemetry(resp: Any, requested_model: str) -> dict[str, Any]:
    usage = getattr(resp, "usage_metadata", None)
    prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0) if usage else 0
    candidate_tokens = int(getattr(usage, "candidates_token_count", 0) or 0) if usage else 0
    thinking_tokens = int(getattr(usage, "thoughts_token_count", 0) or 0) if usage else 0
    total_tokens = int(getattr(usage, "total_token_count", 0) or 0) if usage else 0
    if total_tokens == 0 and (prompt_tokens or candidate_tokens or thinking_tokens):
        total_tokens = prompt_tokens + candidate_tokens + thinking_tokens

    candidates = getattr(resp, "candidates", None) or []
    finish_reason = None
    if candidates:
        fr = getattr(candidates[0], "finish_reason", None)
        finish_reason = str(fr) if fr is not None else None

    actual_model_id = str(
        getattr(resp, "model_version", None)
        or getattr(resp, "model", None)
        or requested_model
    )
    return {
        "actual_model_id": actual_model_id,
        "prompt_tokens": prompt_tokens,
        "candidate_tokens": candidate_tokens,
        "thinking_tokens": thinking_tokens,
        "total_tokens": total_tokens,
        "finish_reason": finish_reason,
    }


def parse_json_text(raw_text: str | None) -> Any:
    raw = (raw_text or "").strip()
    if not raw:
        raise ValueError("Empty response text")
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
    except json.JSONDecodeError:
        obj_match = re.search(r"(\{.*\})", clean, re.DOTALL)
        if obj_match:
            return json.loads(obj_match.group(1))
        arr_match = re.search(r"(\[.*\])", clean, re.DOTALL)
        if arr_match:
            return json.loads(arr_match.group(1))
        raise


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    rank = (len(ordered) - 1) * (pct / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return round(ordered[low], 3)
    weight = rank - low
    return round(ordered[low] * (1.0 - weight) + ordered[high] * weight, 3)


def summarize_numeric(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "min": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0, "mean": 0.0}
    return {
        "count": len(values),
        "min": round(min(values), 3),
        "p50": percentile(values, 50.0),
        "p95": percentile(values, 95.0),
        "max": round(max(values), 3),
        "mean": round(sum(values) / len(values), 3),
    }


def render_compact_schema_spec(schema_source: dict[str, Any] | type[BaseModel]) -> str:
    """Render a compact, readable JSON schema specification for system_instruction."""
    if isinstance(schema_source, type) and issubclass(schema_source, BaseModel):
        schema = schema_source.model_json_schema()
    else:
        schema = dict(schema_source)

    defs = schema.get("$defs") or schema.get("definitions") or {}

    def _resolve_ref(node: dict[str, Any]) -> dict[str, Any]:
        if "$ref" in node:
            ref_name = str(node["$ref"]).split("/")[-1]
            return dict(defs.get(ref_name, {}))
        return node

    def _describe_node(node: dict[str, Any], depth: int = 0) -> Any:
        node = _resolve_ref(node)
        if "anyOf" in node:
            variants = []
            for v in node["anyOf"]:
                v_resolved = _resolve_ref(v)
                if v_resolved.get("type") == "null":
                    variants.append("null")
                else:
                    variants.append(_describe_node(v_resolved, depth))
            return " | ".join(str(x) if not isinstance(x, (dict, list)) else json.dumps(x, ensure_ascii=False) for x in variants)

        typ = node.get("type")
        if typ == "object" or "properties" in node:
            props = node.get("properties", {})
            required_set = set(node.get("required", []))
            out: dict[str, Any] = {}
            for k, prop in props.items():
                prop_r = _resolve_ref(prop)
                req_tag = "required" if k in required_set else "optional"
                desc_val = _describe_node(prop_r, depth + 1)
                if isinstance(desc_val, str):
                    out[k] = f"{desc_val} ({req_tag})"
                else:
                    out[k] = {"_req": req_tag, "schema": desc_val}
            return out
        if typ == "array":
            items = _resolve_ref(node.get("items", {}))
            constraints = []
            if "minItems" in node:
                constraints.append(f"minItems={node['minItems']}")
            if "maxItems" in node:
                constraints.append(f"maxItems={node['maxItems']}")
            c_str = f" [{', '.join(constraints)}]" if constraints else ""
            item_desc = _describe_node(items, depth + 1)
            return [item_desc, f"array{c_str}"] if isinstance(item_desc, dict) else f"array<{item_desc}>{c_str}"

        parts = [str(typ or "any")]
        if "enum" in node:
            parts = [f"enum({', '.join(repr(e) for e in node['enum'])})"]
        elif "const" in node:
            parts = [f"const({node['const']!r})"]
        if "minimum" in node:
            parts.append(f">={node['minimum']}")
        if "maximum" in node:
            parts.append(f"<={node['maximum']}")
        if "minLength" in node:
            parts.append(f"minLen={node['minLength']}")
        if "maxLength" in node:
            parts.append(f"maxLen={node['maxLength']}")
        if "pattern" in node:
            parts.append(f"pattern={node['pattern']}")
        return " ".join(parts)

    compact_obj = _describe_node(schema)
    return json.dumps(compact_obj, ensure_ascii=False, indent=2)


def write_experiment_json(filename: str, data: dict[str, Any]) -> Path:
    EXPERIMENTS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EXPERIMENTS_OUT_DIR / filename
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
