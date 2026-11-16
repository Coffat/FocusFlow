import asyncio
import math
import re
from typing import Any

from src.shared_kernel.application.embedding_port import EmbeddingProviderPort
from src.shared_kernel.config import get_settings

_SUPPORTED_EMBEDDING_PROVIDERS = frozenset({"google_ai_studio", "gemini"})
_PLACEHOLDER_API_KEYS = frozenset(
    {
        "",
        "mock-key",
        "your-api-key",
        "your_api_key",
        "your_google_ai_studio_api_key_here",
        "your_cobhub_or_gemini_api_key_here",
        "changeme",
    }
)
_SECRET_PATTERN = re.compile(
    r"(AIza[0-9A-Za-z\-_]{10,}|sk-[0-9A-Za-z\-_]{12,}|Bearer\s+[0-9A-Za-z\-_.]{8,})",
    re.IGNORECASE,
)
_URL_KEY_PARAM_PATTERN = re.compile(r"([?&]key=)[^&\s'\"]+", re.IGNORECASE)


def _redact_secret(text: str, secret: str) -> str:
    cleaned = text
    if secret:
        cleaned = cleaned.replace(secret, "[REDACTED]")
    cleaned = _SECRET_PATTERN.sub("[REDACTED]", cleaned)
    cleaned = _URL_KEY_PARAM_PATTERN.sub(r"\1[REDACTED]", cleaned)
    return cleaned


class LiteLLMEmbeddingAdapter(EmbeddingProviderPort):
    """Fail-closed Google AI Studio embedding adapter isolated from cobhub LLM gateway."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self._model_override = model
        self._api_key_override = api_key
        self._base_url_override = base_url
        self._dimensions_override = dimensions
        self._base_url: str = ""
        self._model: str = "gemini/gemini-embedding-2"
        self._dimensions: int = 768
        self._settings = get_settings()

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def _settings(self) -> Any:
        return self.__settings

    @_settings.setter
    def _settings(self, value: Any) -> None:
        self.__settings = value
        self._base_url = self._compute_base_url()
        self._model = self._compute_model()
        self._dimensions = self._compute_dimensions()

    def _resolve_provider(self) -> str:
        return (getattr(self._settings, "embedding_provider", "") or "").strip().lower()

    def _resolve_api_key(self) -> str:
        raw = (
            self._api_key_override
            if self._api_key_override is not None
            else getattr(self._settings, "embedding_api_key", "")
        )
        return (raw or "").strip()

    def _compute_base_url(self) -> str:
        raw = (
            self._base_url_override
            if self._base_url_override is not None
            else getattr(self._settings, "embedding_base_url", "")
        )
        return (raw or "").strip()

    def _compute_dimensions(self) -> int:
        if self._dimensions_override is not None:
            return int(self._dimensions_override)
        raw = getattr(self._settings, "embedding_dimensions", 768)
        return int(raw) if raw is not None else 0

    def _compute_model(self) -> str:
        if self._model_override is not None:
            configured = self._model_override.strip()
        else:
            configured = (getattr(self._settings, "embedding_model", "") or "").strip()
        if not configured:
            return ""
        provider = self._resolve_provider()
        if provider in _SUPPORTED_EMBEDDING_PROVIDERS and "/" not in configured:
            return f"gemini/{configured}"
        return configured

    async def embed(
        self,
        texts: list[str],
        *,
        task_type: str | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []

        provider = self._resolve_provider()
        if provider not in _SUPPORTED_EMBEDDING_PROVIDERS:
            raise RuntimeError(
                "AI_EMBEDDING_PROVIDER_NOT_CONFIGURED: "
                f"Unsupported embedding_provider={getattr(self._settings, 'embedding_provider', None)!r}."
            )

        model = self._model
        if not model:
            raise RuntimeError(
                "AI_EMBEDDING_PROVIDER_NOT_CONFIGURED: Missing EMBEDDING_MODEL for embeddings."
            )

        if self._dimensions <= 0:
            raise RuntimeError(
                "AI_EMBEDDING_PROVIDER_NOT_CONFIGURED: "
                f"Invalid embedding_dimensions={self._dimensions}."
            )

        api_key = self._resolve_api_key()
        lowered_key = api_key.lower()
        if lowered_key in _PLACEHOLDER_API_KEYS or lowered_key.startswith("your_"):
            raise RuntimeError(
                "AI_EMBEDDING_PROVIDER_NOT_CONFIGURED: "
                "Missing valid EMBEDDING_API_KEY / GEMINI_API_KEY for embeddings."
            )

        import litellm

        call_kwargs: dict[str, Any] = {
            "model": model,
            "input": texts,
            "api_key": api_key,
            "api_base": self._base_url or None,
            "dimensions": self._dimensions,
        }
        if task_type is not None:
            call_kwargs["task_type"] = task_type

        try:
            response: Any = await asyncio.wait_for(
                litellm.aembedding(**call_kwargs),
                timeout=10.0,
            )
        except Exception as exc:
            safe_detail = _redact_secret(str(exc), api_key)
            raise RuntimeError(
                f"AI_EMBEDDING_FAILED: Embedding model failed ({model}): {safe_detail}"
            ) from exc

        data = getattr(response, "data", None)
        if isinstance(response, dict):
            data = response.get("data")
        if not isinstance(data, list) or len(data) != len(texts):
            raise RuntimeError(
                f"AI_EMBEDDING_FAILED: Invalid embedding response shape from model={model}"
            )

        vectors: list[list[float]] = []
        for item in data:
            emb = (
                item.get("embedding")
                if isinstance(item, dict)
                else getattr(item, "embedding", None)
            )
            if not isinstance(emb, list):
                raise RuntimeError(
                    f"AI_EMBEDDING_FAILED: Invalid embedding item shape from model={model}"
                )
            if len(emb) != self._dimensions:
                raise RuntimeError(
                    "AI_EMBEDDING_DIMENSION_MISMATCH: "
                    f"Expected {self._dimensions} dimensions, got {len(emb)} from model={model}"
                )
            vec = [float(v) for v in emb]
            norm = math.sqrt(sum(v * v for v in vec))
            if not math.isfinite(norm) or norm <= 0.0:
                raise RuntimeError(
                    "AI_EMBEDDING_INVALID_NORM: "
                    f"Embedding vector has invalid L2 norm={norm} from model={model}"
                )
            if abs(norm - 1.0) > 1e-4:
                vec = [v / norm for v in vec]
            vectors.append(vec)
        return vectors
