import hashlib
import math

from src.shared_kernel.application.embedding_port import EmbeddingProviderPort


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
