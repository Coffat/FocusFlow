import asyncio
import os
import re
from typing import Any

from src.shared_kernel.application.embedding_port import EmbeddingProviderPort
from src.shared_kernel.config import get_settings


class LiteLLMEmbeddingAdapter(EmbeddingProviderPort):
    """Fail-closed provider-agnostic embedding adapter via LiteLLM and cobhub gateway."""

    dimensions = 768

    def __init__(self, *, model: str | None = None, api_key: str | None = None) -> None:
        self._model_override = model
        self._api_key_override = api_key
        self._base_url: str = ""
        self._model: str = "gemini/gemini-embedding-2"
        self._settings = get_settings()

    @property
    def _settings(self) -> Any:
        return self.__settings

    @_settings.setter
    def _settings(self, value: Any) -> None:
        self.__settings = value
        self._base_url = self._compute_base_url()
        self._model = self._compute_model()

    def _resolve_provider(self) -> str:
        return (getattr(self._settings, "llm_provider", "") or "").strip().lower()

    def _resolve_api_key(self) -> str:
        raw = (
            self._api_key_override
            if self._api_key_override is not None
            else getattr(self._settings, "llm_api_key", "")
        )
        return (raw or "").strip()

    def _compute_base_url(self) -> str:
        base_url = (getattr(self._settings, "llm_base_url", "") or "").strip()
        if base_url and (os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_DOCKER")):
            base_url = re.sub(
                r"^http://(127\.0\.0\.1|localhost)(:\d+)",
                r"http://host.docker.internal\2",
                base_url,
            )
        return base_url

    def _compute_model(self) -> str:
        if self._model_override is not None:
            return self._model_override
        provider = self._resolve_provider()
        configured = (
            getattr(self._settings, "llm_embedding_model", "") or "gemini/gemini-embedding-2"
        ).strip()
        if provider == "gemini":
            return configured if "/" in configured else f"gemini/{configured}"
        if provider == "openai":
            return configured or "text-embedding-3-small"
        return configured if "/" in configured else f"{provider}/{configured}"

    def _candidate_models(self) -> tuple[str, ...]:
        return (self._model,)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        provider = self._resolve_provider()
        if not provider or provider in ("mock", "local_mock"):
            raise RuntimeError(
                "AI_EMBEDDING_PROVIDER_NOT_CONFIGURED: "
                f"Unsupported llm_provider={getattr(self._settings, 'llm_provider', None)!r}."
            )
        if provider == "gemini" and not self._base_url:
            raise RuntimeError(
                "AI_EMBEDDING_PROVIDER_NOT_CONFIGURED: Missing LLM_BASE_URL for cobhub gateway."
            )
        api_key = self._resolve_api_key()
        if not api_key or api_key in ("mock-key", "your-api-key"):
            raise RuntimeError(
                "AI_EMBEDDING_PROVIDER_NOT_CONFIGURED: Missing valid LLM_API_KEY for embeddings."
            )

        import litellm

        model = self._model
        try:
            response: Any = await asyncio.wait_for(
                litellm.aembedding(
                    model=model,
                    input=texts,
                    api_key=api_key,
                    api_base=self._base_url or None,
                    dimensions=self.dimensions,
                ),
                timeout=3.0,
            )
            data = getattr(response, "data", None)
            if isinstance(response, dict):
                data = response.get("data")
            if isinstance(data, list) and len(data) == len(texts):
                vectors: list[list[float]] = []
                valid = True
                for item in data:
                    emb = (
                        item.get("embedding")
                        if isinstance(item, dict)
                        else getattr(item, "embedding", None)
                    )
                    if isinstance(emb, list) and len(emb) >= self.dimensions:
                        vectors.append([float(v) for v in emb[: self.dimensions]])
                    else:
                        valid = False
                        break
                if valid:
                    return vectors
            raise RuntimeError(f"Invalid embedding response shape from model={model}")
        except Exception as exc:
            raise RuntimeError(
                f"AI_EMBEDDING_FAILED: Embedding model failed ({model}): {exc}"
            ) from exc
