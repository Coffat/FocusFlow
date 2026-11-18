from __future__ import annotations

import copy
import json
import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .models import ContextLayer, HarnessContext
from .untrusted_context import SENSITIVE_DICT_KEYS

_LAYER_MARKER_RE = re.compile(
    r"\[\s*(/?)\s*((?:SYSTEM|WORKFLOW|USER|LEARNING|RUNTIME)_CONTEXT)\s*\]",
    re.IGNORECASE,
)

_PRIORITY_ORDER: tuple[ContextLayer, ...] = (
    ContextLayer.LEARNING,
    ContextLayer.USER,
    ContextLayer.WORKFLOW,
    ContextLayer.RUNTIME,
    ContextLayer.SYSTEM,
)

_LOW_PRIORITY_KEYS: tuple[str, ...] = (
    "rag_chunks",
    "concept_masteries",
    "active_memories",
    "information_gaps",
    "feedback",
    "planning_context",
)


@dataclass(frozen=True, slots=True)
class AssembledContext:
    text: str
    layer_tokens: dict[ContextLayer, int]
    total_tokens: int
    truncated_layers: tuple[ContextLayer, ...]


class ContextEngine:
    """Assemble five explicit context layers under a deterministic token budget."""

    _ALLOCATIONS: dict[ContextLayer, float] = {
        ContextLayer.SYSTEM: 0.10,
        ContextLayer.WORKFLOW: 0.15,
        ContextLayer.USER: 0.15,
        ContextLayer.LEARNING: 0.45,
        ContextLayer.RUNTIME: 0.15,
    }
    _FORBIDDEN_RAW_KEYS = frozenset({"study_sessions", "study_notes", "schedule_change_logs"})
    _FORBIDDEN_KEYS = _FORBIDDEN_RAW_KEYS | SENSITIVE_DICT_KEYS

    def __init__(
        self,
        *,
        total_token_budget: int = 8_000,
        token_counter: Callable[[str], int] | None = None,
    ) -> None:
        if total_token_budget < 500:
            raise ValueError("total_token_budget must be >= 500")
        self._total_token_budget = total_token_budget
        self._token_counter = token_counter
        self._token_cache: dict[str, int] = {}

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        cached = self._token_cache.get(text)
        if cached is not None:
            return cached
        if self._token_counter is not None:
            count = max(1, int(self._token_counter(text)))
        else:
            ascii_chars = sum(1 for ch in text if ord(ch) < 128)
            non_ascii_chars = len(text) - ascii_chars
            # Conservative estimate for Vietnamese diacritics and compact JSON punctuation.
            count = max(1, math.ceil(ascii_chars / 3.0 + non_ascii_chars / 1.35))
        if len(self._token_cache) >= 512:
            self._token_cache.clear()
        self._token_cache[text] = count
        return count

    @staticmethod
    def _compact_json(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def _reject_forbidden_keys(cls, value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if str(key).lower() in cls._FORBIDDEN_KEYS:
                    raise ValueError(
                        f"Raw learning history or PII key is forbidden in ContextEngine: {key}"
                    )
                cls._reject_forbidden_keys(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                cls._reject_forbidden_keys(item)

    @classmethod
    def _escape_layer_markers(cls, value: Any) -> Any:
        if isinstance(value, str):
            return _LAYER_MARKER_RE.sub(
                lambda m: f"&#91;{m.group(1)}{m.group(2)}&#93;",
                value,
            )
        if isinstance(value, dict):
            return {str(k): cls._escape_layer_markers(v) for k, v in value.items()}
        if isinstance(value, list):
            return [cls._escape_layer_markers(item) for item in value]
        if isinstance(value, tuple):
            return [cls._escape_layer_markers(item) for item in value]
        return value

    def _fits(self, payload: dict[str, Any], token_budget: int) -> bool:
        return self._estimate_tokens(self._compact_json(payload)) <= token_budget

    @staticmethod
    def _collect_list_refs(payload: dict[str, Any]) -> list[tuple[dict[str, Any], str, int]]:
        refs: list[tuple[dict[str, Any], str, int]] = []
        priority_rank = {key: idx for idx, key in enumerate(_LOW_PRIORITY_KEYS)}

        def _walk(node: Any) -> None:
            if isinstance(node, dict):
                for k, v in node.items():
                    if isinstance(v, list) and v:
                        refs.append((node, k, priority_rank.get(k, len(_LOW_PRIORITY_KEYS))))
                    elif isinstance(v, (dict, list)):
                        _walk(v)
            elif isinstance(node, list):
                for item in node:
                    _walk(item)

        _walk(payload)
        refs.sort(key=lambda entry: (entry[2], -len(entry[0][entry[1]])))
        return refs

    @staticmethod
    def _find_longest_string_ref(payload: dict[str, Any]) -> tuple[Any, int | str, str] | None:
        best: tuple[Any, int | str, str] | None = None

        def _walk(node: Any) -> None:
            nonlocal best
            if isinstance(node, dict):
                for k, v in node.items():
                    if isinstance(v, str):
                        if best is None or len(v) > len(best[2]):
                            best = (node, k, v)
                    elif isinstance(v, (dict, list)):
                        _walk(v)
            elif isinstance(node, list):
                for idx, v in enumerate(node):
                    if isinstance(v, str):
                        if best is None or len(v) > len(best[2]):
                            best = (node, idx, v)
                    elif isinstance(v, (dict, list)):
                        _walk(v)

        _walk(payload)
        return best

    def _truncate_payload_to_budget(
        self, payload: dict[str, Any], token_budget: int
    ) -> tuple[str, bool]:
        compact = self._compact_json(payload)
        if self._estimate_tokens(compact) <= token_budget:
            return compact, False

        working: dict[str, Any] = copy.deepcopy(payload)

        # Phase A: Drop tail items from lower-priority lists first while preserving valid JSON.
        for parent, key, _rank in self._collect_list_refs(working):
            original_list = list(parent[key])
            lo, hi = 0, len(original_list)
            best_len = 0
            while lo <= hi:
                mid = (lo + hi) // 2
                parent[key] = original_list[:mid]
                if self._fits(working, token_budget):
                    best_len = mid
                    lo = mid + 1
                else:
                    hi = mid - 1
            parent[key] = original_list[:best_len]
            if self._fits(working, token_budget):
                return self._compact_json(working), True

        # Phase B: Shrink the longest string fields via binary search.
        suffix = "…[TRUNCATED]"
        for _ in range(32):
            if self._fits(working, token_budget):
                return self._compact_json(working), True
            ref = self._find_longest_string_ref(working)
            if ref is None or len(ref[2]) <= len(suffix):
                break
            container, key_or_idx, raw_str = ref
            lo, hi = 0, len(raw_str)
            best_str = ""
            while lo <= hi:
                mid = (lo + hi) // 2
                candidate = f"{raw_str[:mid]}{suffix}" if mid > 0 else ""
                container[key_or_idx] = candidate
                if self._fits(working, token_budget):
                    best_str = candidate
                    lo = mid + 1
                else:
                    hi = mid - 1
            if best_str:
                container[key_or_idx] = best_str
                return self._compact_json(working), True
            container[key_or_idx] = ""

        # Phase C: Drop lowest-priority top-level keys as a last resort.
        ordered_keys = sorted(
            working.keys(),
            key=lambda k: (
                _LOW_PRIORITY_KEYS.index(k) if k in _LOW_PRIORITY_KEYS else len(_LOW_PRIORITY_KEYS)
            ),
        )
        for key in ordered_keys:
            if self._fits(working, token_budget):
                return self._compact_json(working), True
            working.pop(key, None)

        if self._fits(working, token_budget):
            return self._compact_json(working), True
        return "{}", True

    def _allocate_layer_budgets(
        self,
        escaped_payloads: dict[ContextLayer, dict[str, Any]],
    ) -> dict[ContextLayer, int]:
        raw_tokens: dict[ContextLayer, int] = {
            layer: (self._estimate_tokens(self._compact_json(payload)) if payload else 0)
            for layer, payload in escaped_payloads.items()
        }
        budgets: dict[ContextLayer, int] = {}
        surplus = self._total_token_budget

        for layer in ContextLayer:
            if not escaped_payloads[layer]:
                budgets[layer] = 0
                continue
            base_budget = int(self._total_token_budget * self._ALLOCATIONS[layer])
            used = min(base_budget, raw_tokens[layer])
            budgets[layer] = used
            surplus -= used

        # Redistribute unused budget from empty or under-budget layers in priority order.
        if surplus > 0:
            for layer in _PRIORITY_ORDER:
                if surplus <= 0:
                    break
                if not escaped_payloads[layer]:
                    continue
                need = raw_tokens[layer] - budgets[layer]
                if need > 0:
                    grant = min(need, surplus)
                    budgets[layer] += grant
                    surplus -= grant

        # Any remaining surplus goes to the highest-priority non-empty layer as headroom.
        if surplus > 0:
            for layer in _PRIORITY_ORDER:
                if escaped_payloads[layer]:
                    budgets[layer] += surplus
                    break

        return budgets

    def assemble(self, context: HarnessContext) -> AssembledContext:
        raw_payloads: dict[ContextLayer, dict[str, Any]] = {
            ContextLayer.SYSTEM: context.system,
            ContextLayer.WORKFLOW: context.workflow,
            ContextLayer.USER: context.user,
            ContextLayer.LEARNING: context.learning,
            ContextLayer.RUNTIME: context.runtime,
        }
        escaped_payloads: dict[ContextLayer, dict[str, Any]] = {}
        for layer, payload in raw_payloads.items():
            self._reject_forbidden_keys(payload)
            escaped_payloads[layer] = self._escape_layer_markers(payload) if payload else {}

        budgets = self._allocate_layer_budgets(escaped_payloads)

        rendered: list[str] = []
        layer_tokens: dict[ContextLayer, int] = {}
        truncated: list[ContextLayer] = []
        for layer in ContextLayer:
            payload = escaped_payloads[layer]
            if not payload:
                layer_tokens[layer] = 0
                continue
            text, was_truncated = self._truncate_payload_to_budget(payload, budgets[layer])
            if was_truncated:
                truncated.append(layer)
            tokens = self._estimate_tokens(text)
            layer_tokens[layer] = tokens
            rendered.append(f"[{layer.value}_CONTEXT]\n{text}\n[/{layer.value}_CONTEXT]")

        return AssembledContext(
            text="\n".join(rendered),
            layer_tokens=layer_tokens,
            total_tokens=sum(layer_tokens.values()),
            truncated_layers=tuple(truncated),
        )
