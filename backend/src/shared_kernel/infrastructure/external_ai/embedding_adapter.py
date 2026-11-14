import hashlib
import math
from typing import Any

from src.shared_kernel.application.embedding_port import EmbeddingProviderPort
from src.shared_kernel.config import get_settings


class MockEmbeddingAdapter(EmbeddingProviderPort):
    """Network-free deterministic embeddings for tests, CI and offline defense."""

    dimensions = 768

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    @classmethod
    def _embed_one(cls, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        values = [
            ((digest[index % len(digest)] / 255.0) * 2.0) - 1.0 for index in range(cls.dimensions)
        ]
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]


class LiteLLMEmbeddingAdapter(EmbeddingProviderPort):
    """Provider-agnostic embedding adapter via LiteLLM with deterministic offline fallback."""

    dimensions = 768

    def __init__(self, *, model: str | None = None, api_key: str | None = None) -> None:
        settings = get_settings()
        self._provider = settings.llm_provider.strip().lower()
        self._api_key = api_key if api_key is not None else settings.llm_api_key
        if model is not None:
            self._model = model
        elif self._provider == "gemini":
            self._model = "gemini/text-embedding-004"
        elif self._provider == "openai":
            self._model = "text-embedding-3-small"
        else:
            self._model = f"{self._provider}/text-embedding-004"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._provider == "mock" or not self._api_key or self._api_key == "mock-key":
            return await MockEmbeddingAdapter().embed(texts)
        try:
            import litellm

            response: Any = await litellm.aembedding(
                model=self._model,
                input=texts,
                api_key=self._api_key,
                dimensions=self.dimensions,
            )
            data = getattr(response, "data", None)
            if isinstance(response, dict):
                data = response.get("data")
            if isinstance(data, list) and len(data) == len(texts):
                vectors: list[list[float]] = []
                for item in data:
                    emb = (
                        item.get("embedding")
                        if isinstance(item, dict)
                        else getattr(item, "embedding", None)
                    )
                    if isinstance(emb, list) and len(emb) >= self.dimensions:
                        vectors.append([float(v) for v in emb[: self.dimensions]])
                    else:
                        return await MockEmbeddingAdapter().embed(texts)
                return vectors
        except Exception:
            pass
        return await MockEmbeddingAdapter().embed(texts)
