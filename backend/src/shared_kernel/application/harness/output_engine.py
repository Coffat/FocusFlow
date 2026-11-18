from typing import Any, TypeVar, cast

from pydantic import TypeAdapter, ValidationError

T = TypeVar("T")


class OutputEngine:
    """Strict structured-output boundary for all external model responses."""

    @staticmethod
    def validate(payload: Any, schema: type[T] | dict[str, Any] | None) -> Any:
        if schema is None:
            return payload
        if isinstance(schema, dict):
            if not isinstance(payload, dict):
                raise ValueError("AI_SCHEMA_VALIDATION_ERROR: Expected JSON object payload")
            required = schema.get("required")
            if isinstance(required, list):
                missing = [k for k in required if k not in payload]
                if missing:
                    raise ValueError(f"AI_SCHEMA_VALIDATION_ERROR: Missing required keys {missing}")
            return cast(dict[str, Any], payload)
        try:
            return TypeAdapter(schema).validate_python(payload, strict=True)
        except ValidationError as exc:
            raise ValueError(f"AI_SCHEMA_VALIDATION_ERROR: {exc}") from exc
