from typing import Protocol
from uuid import UUID

from src.planning.domain.models.knowledge_source import KnowledgeChunk, KnowledgeSource


class KnowledgeSourceRepositoryPort(Protocol):
    async def save_source(self, source: KnowledgeSource) -> KnowledgeSource: ...

    async def get_source_for_user(
        self, source_id: UUID, user_id: UUID
    ) -> KnowledgeSource | None: ...

    async def list_sources_for_goal(
        self, goal_id: UUID, user_id: UUID
    ) -> list[KnowledgeSource]: ...

    async def replace_chunks(self, source_id: UUID, chunks: list[KnowledgeChunk]) -> None: ...

    async def hybrid_search(
        self,
        *,
        goal_id: UUID,
        query: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[KnowledgeChunk]: ...
