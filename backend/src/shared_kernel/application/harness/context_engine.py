import json
from dataclasses import dataclass
from typing import Any

from .models import ContextLayer, HarnessContext


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

    def __init__(self, *, total_token_budget: int = 8_000) -> None:
        if total_token_budget < 500:
            raise ValueError("total_token_budget must be >= 500")
        self._total_token_budget = total_token_budget

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, (len(text) + 3) // 4)

    @staticmethod
    def _compact_json(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def _reject_raw_history(cls, payload: dict[str, Any]) -> None:
        forbidden = cls._FORBIDDEN_RAW_KEYS.intersection(payload)
        if forbidden:
            names = ", ".join(sorted(forbidden))
            raise ValueError(f"Raw learning history is forbidden in ContextEngine: {names}")

    @staticmethod
    def _truncate(text: str, token_budget: int) -> tuple[str, bool]:
        char_budget = max(4, token_budget * 4)
        if len(text) <= char_budget:
            return text, False
        return f"{text[: char_budget - 15]}…[TRUNCATED]", True

    def assemble(self, context: HarnessContext) -> AssembledContext:
        payloads = {
            ContextLayer.SYSTEM: context.system,
            ContextLayer.WORKFLOW: context.workflow,
            ContextLayer.USER: context.user,
            ContextLayer.LEARNING: context.learning,
            ContextLayer.RUNTIME: context.runtime,
        }
        rendered: list[str] = []
        layer_tokens: dict[ContextLayer, int] = {}
        truncated: list[ContextLayer] = []
        for layer, payload in payloads.items():
            self._reject_raw_history(payload)
            budget = int(self._total_token_budget * self._ALLOCATIONS[layer])
            text, was_truncated = self._truncate(self._compact_json(payload), budget)
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
