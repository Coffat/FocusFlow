from typing import Protocol


class EmbeddingProviderPort(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one 768-dimensional embedding for each input text."""
        ...
