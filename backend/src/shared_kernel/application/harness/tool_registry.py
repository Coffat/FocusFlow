import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from src.shared_kernel.application.llm_port import LLMToolDeclarationDTO

from .models import ToolResultEnvelope

logger = logging.getLogger(__name__)

ToolHandler = Callable[[dict[str, Any]], Awaitable[ToolResultEnvelope]]

_SENSITIVE_KEY_MARKERS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "email",
    "phone",
    "card",
)


def _normalize_stage(stage: str | Enum) -> str:
    if isinstance(stage, Enum):
        return str(stage.value)
    return str(stage)


def _redact_audit_value(key: str, value: Any) -> Any:
    key_lower = key.lower()
    if any(marker in key_lower for marker in _SENSITIVE_KEY_MARKERS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _redact_audit_value(str(k), v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_audit_value(key, item) for item in value[:20]]
    if isinstance(value, str) and len(value) > 200:
        return value[:200] + "...[TRUNCATED]"
    return value


def _check_json_type(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "object":
        return isinstance(value, dict)
    return True


def _validate_arguments_against_schema(
    arguments: dict[str, Any],
    schema: dict[str, Any],
) -> str | None:
    """Validate tool call arguments against declaration JSON Schema; return error message or None."""
    if not schema:
        return None
    required_fields = schema.get("required", [])
    if isinstance(required_fields, (list, tuple)):
        for req in required_fields:
            if req not in arguments or arguments[req] is None:
                return f"Missing required argument: {req!r}"

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return None

    if schema.get("additionalProperties") is False:
        unknown = set(arguments) - set(properties)
        if unknown:
            return f"Unknown arguments not allowed by schema: {sorted(unknown)}"

    for key, val in arguments.items():
        if val is None or key not in properties:
            continue
        prop_schema = properties.get(key)
        if not isinstance(prop_schema, dict):
            continue
        expected_type = prop_schema.get("type")
        if isinstance(expected_type, str) and not _check_json_type(val, expected_type):
            return f"Argument {key!r} must be of type {expected_type!r}, got {type(val).__name__}"
        enum_vals = prop_schema.get("enum")
        if isinstance(enum_vals, list) and val not in enum_vals:
            return f"Argument {key!r} must be one of {enum_vals}, got {val!r}"
        if isinstance(val, str):
            min_len = prop_schema.get("minLength")
            max_len = prop_schema.get("maxLength")
            if isinstance(min_len, int) and len(val) < min_len:
                return f"Argument {key!r} length must be >= {min_len}"
            if isinstance(max_len, int) and len(val) > max_len:
                return f"Argument {key!r} length must be <= {max_len}"
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            minimum = prop_schema.get("minimum")
            maximum = prop_schema.get("maximum")
            if isinstance(minimum, (int, float)) and val < minimum:
                return f"Argument {key!r} must be >= {minimum}"
            if isinstance(maximum, (int, float)) and val > maximum:
                return f"Argument {key!r} must be <= {maximum}"
        if isinstance(val, list):
            min_items = prop_schema.get("minItems")
            max_items = prop_schema.get("maxItems")
            if isinstance(min_items, int) and len(val) < min_items:
                return f"Argument {key!r} must have at least {min_items} items"
            if isinstance(max_items, int) and len(val) > max_items:
                return f"Argument {key!r} must have at most {max_items} items"
            item_schema = prop_schema.get("items")
            if isinstance(item_schema, dict) and isinstance(item_schema.get("type"), str):
                item_type = item_schema["type"]
                for idx, item in enumerate(val):
                    if not _check_json_type(item, item_type):
                        return f"Argument '{key}[{idx}]' must be of type {item_type!r}"
    return None


def _truncate_data(
    data: dict[str, Any],
    *,
    max_items: int,
    max_output_bytes: int,
) -> tuple[dict[str, Any], bool]:
    truncated = False

    def _bound_value(val: Any) -> Any:
        nonlocal truncated
        if isinstance(val, dict):
            return {str(k): _bound_value(v) for k, v in val.items()}
        if isinstance(val, list):
            if len(val) > max_items:
                truncated = True
                return [_bound_value(item) for item in val[:max_items]]
            return [_bound_value(item) for item in val]
        if isinstance(val, str) and len(val.encode("utf-8")) > max_output_bytes // 2:
            truncated = True
            return val[: max(64, max_output_bytes // 4)] + "...[TRUNCATED]"
        return val

    bounded = _bound_value(dict(data))
    serialized = json.dumps(bounded, ensure_ascii=False, default=str).encode("utf-8")
    if len(serialized) > max_output_bytes:
        truncated = True
        preview = serialized[: max(64, max_output_bytes - 128)].decode("utf-8", errors="ignore")
        bounded = {
            "truncated": True,
            "preview": preview + "...[TRUNCATED]",
        }
    elif truncated:
        bounded = {**bounded, "truncated": True}
    return bounded, truncated


@dataclass(frozen=True, slots=True)
class ToolAuditRecord:
    tool_name: str
    stage: str
    status: str
    sanitized_arguments: dict[str, Any]
    truncated: bool = False
    error_code: str | None = None
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    declaration: LLMToolDeclarationDTO
    allowed_stages: frozenset[str]
    handler: ToolHandler
    timeout_seconds: float | None = None

    def __post_init__(self) -> None:
        normalized = frozenset(_normalize_stage(s) for s in self.allowed_stages)
        object.__setattr__(self, "allowed_stages", normalized)


class ToolRegistry:
    """Contract-bound registry with explicit workflow-stage permissions, schema validation, timeout, and output bounds."""

    def __init__(
        self,
        tools: Iterable[RegisteredTool] = (),
        *,
        default_timeout_seconds: float = 5.0,
        max_items: int = 20,
        max_output_bytes: int = 16384,
    ) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._default_timeout_seconds = max(0.05, default_timeout_seconds)
        self._max_items = max(1, max_items)
        self._max_output_bytes = max(256, max_output_bytes)
        self._audit_log: list[ToolAuditRecord] = []
        for tool in tools:
            self.register(tool)

    @property
    def audit_log(self) -> tuple[ToolAuditRecord, ...]:
        return tuple(self._audit_log)

    def register(self, tool: RegisteredTool) -> None:
        name = tool.declaration.name
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        if not tool.allowed_stages:
            raise ValueError(f"Tool must declare at least one allowed stage: {name}")
        self._tools[name] = tool

    def declarations_for(self, stage: str | Enum) -> list[LLMToolDeclarationDTO]:
        stage_str = _normalize_stage(stage)
        return [
            tool.declaration for tool in self._tools.values() if stage_str in tool.allowed_stages
        ]

    async def dispatch(
        self,
        *,
        stage: str | Enum,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        stage_str = _normalize_stage(stage)
        tool = self._tools.get(tool_name)
        if tool is None or stage_str not in tool.allowed_stages:
            raise PermissionError(f"Tool {tool_name!r} is not allowed in stage {stage_str!r}")
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be a JSON object")

        sanitized_args = {str(k): _redact_audit_value(str(k), v) for k, v in arguments.items()}
        schema_error = _validate_arguments_against_schema(
            arguments,
            tool.declaration.parameters_schema,
        )
        if schema_error is not None:
            self._audit_log.append(
                ToolAuditRecord(
                    tool_name=tool_name,
                    stage=stage_str,
                    status="error",
                    sanitized_arguments=sanitized_args,
                    error_code="INVALID_TOOL_ARGUMENTS",
                )
            )
            return ToolResultEnvelope(
                status="error",
                summary=f"Invalid arguments for tool {tool_name}: {schema_error}",
                data={
                    "error_code": "INVALID_TOOL_ARGUMENTS",
                    "reason": schema_error,
                },
            ).as_dict()

        timeout = (
            tool.timeout_seconds
            if tool.timeout_seconds is not None and tool.timeout_seconds > 0
            else self._default_timeout_seconds
        )
        try:
            result = await asyncio.wait_for(tool.handler(arguments), timeout=timeout)
        except TimeoutError:
            self._audit_log.append(
                ToolAuditRecord(
                    tool_name=tool_name,
                    stage=stage_str,
                    status="error",
                    sanitized_arguments=sanitized_args,
                    error_code="TOOL_TIMEOUT",
                )
            )
            return ToolResultEnvelope(
                status="error",
                summary=f"Tool {tool_name} timed out after {timeout:.2f}s",
                data={
                    "error_code": "TOOL_TIMEOUT",
                    "timeout_seconds": timeout,
                },
            ).as_dict()
        except Exception as exc:
            logger.warning(
                "Tool %s execution failed in stage %s: %s",
                tool_name,
                stage_str,
                type(exc).__name__,
            )
            self._audit_log.append(
                ToolAuditRecord(
                    tool_name=tool_name,
                    stage=stage_str,
                    status="error",
                    sanitized_arguments=sanitized_args,
                    error_code=getattr(exc, "code", type(exc).__name__),
                )
            )
            return ToolResultEnvelope(
                status="error",
                summary=f"Tool {tool_name} failed: {type(exc).__name__}",
                data={
                    "error_code": str(getattr(exc, "code", "TOOL_EXECUTION_ERROR")),
                    "reason": str(exc)[:300],
                },
            ).as_dict()

        normalized_status = "success" if result.status == "OK" else result.status
        if normalized_status not in {"success", "warning", "error"}:
            raise ValueError(f"Invalid tool result status: {result.status}")

        bounded_data, was_truncated = _truncate_data(
            result.data,
            max_items=self._max_items,
            max_output_bytes=self._max_output_bytes,
        )
        final_envelope = replace(
            result,
            status=normalized_status,
            data=bounded_data,
        )
        self._audit_log.append(
            ToolAuditRecord(
                tool_name=tool_name,
                stage=stage_str,
                status=normalized_status,
                sanitized_arguments=sanitized_args,
                truncated=was_truncated,
            )
        )
        return final_envelope.as_dict()
