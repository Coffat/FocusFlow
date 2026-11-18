from typing import Protocol


class EmbeddingProviderPort(Protocol):
    async def embed(
        self,
        texts: list[str],
        *,
        task_type: str | None = None,
    ) -> list[list[float]]:
        """Return one 768-dimensional L2-normalized embedding for each input text."""
        ...
