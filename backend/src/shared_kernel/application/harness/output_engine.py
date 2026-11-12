from typing import Any, TypeVar

from pydantic import TypeAdapter, ValidationError

T = TypeVar("T")


class OutputEngine:
    """Strict structured-output boundary for all external model responses."""

    @staticmethod
    def validate(payload: Any, schema: type[T]) -> T:
        try:
            return TypeAdapter(schema).validate_python(payload, strict=True)
        except ValidationError as exc:
            raise ValueError(f"AI_SCHEMA_VALIDATION_ERROR: {exc}") from exc
