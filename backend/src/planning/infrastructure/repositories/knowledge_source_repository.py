from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.planning.application.knowledge.hybrid_retrieval import reciprocal_rank_fusion
from src.planning.application.ports.knowledge_source_repository_port import (
    KnowledgeSourceRepositoryPort,
)
from src.planning.domain.models.knowledge_source import (
    KnowledgeChunk,
    KnowledgeIngestionStatus,
    KnowledgeSource,
    KnowledgeSourceType,
)
from src.planning.infrastructure.orm.knowledge_orm import KnowledgeChunkORM, KnowledgeSourceORM


class SqlAlchemyKnowledgeSourceRepository(KnowledgeSourceRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_source(self, source: KnowledgeSource) -> KnowledgeSource:
        row = await self._session.get(KnowledgeSourceORM, source.id)
        if row is None:
            row = KnowledgeSourceORM(id=source.id, user_id=source.user_id, goal_id=source.goal_id)
            self._session.add(row)
        row.source_type = source.source_type.value
        row.title = source.title
        row.source_uri = source.source_uri
        row.content_hash = source.content_hash
        row.ingestion_status = source.ingestion_status.value
        row.chunk_count = source.chunk_count
        row.provenance_metadata = dict(source.provenance_metadata)
        row.error_detail = source.error_detail
        row.created_at = source.created_at
        row.updated_at = source.updated_at
        await self._session.flush()
        return self._source_to_domain(row)

    async def get_source_for_user(self, source_id: UUID, user_id: UUID) -> KnowledgeSource | None:
        row = await self._session.scalar(
            select(KnowledgeSourceORM).where(
                KnowledgeSourceORM.id == source_id, KnowledgeSourceORM.user_id == user_id
            )
        )
        return self._source_to_domain(row) if row else None

    async def list_sources_for_goal(self, goal_id: UUID, user_id: UUID) -> list[KnowledgeSource]:
        rows = (
            await self._session.scalars(
                select(KnowledgeSourceORM)
                .where(
                    KnowledgeSourceORM.goal_id == goal_id,
                    KnowledgeSourceORM.user_id == user_id,
                )
                .order_by(KnowledgeSourceORM.created_at.desc())
            )
        ).all()
        return [self._source_to_domain(row) for row in rows]

    async def replace_chunks(self, source_id: UUID, chunks: list[KnowledgeChunk]) -> None:
        await self._session.execute(
            delete(KnowledgeChunkORM).where(KnowledgeChunkORM.source_id == source_id)
        )
        for chunk in chunks:
            self._session.add(
                KnowledgeChunkORM(
                    id=chunk.id,
                    source_id=chunk.source_id,
                    goal_id=chunk.goal_id,
                    chunk_index=chunk.chunk_index,
                    section_title=chunk.section_title,
                    page_number=chunk.page_number,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    embedding=list(chunk.embedding) if chunk.embedding else None,
                    provenance_json=dict(chunk.provenance_json),
                    created_at=chunk.created_at,
                )
            )
        await self._session.flush()

    async def hybrid_search(
        self,
        *,
        goal_id: UUID,
        query: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[KnowledgeChunk]:
        candidate_limit = max(1, limit * 2)
        ts_query = func.websearch_to_tsquery("simple", query)
        lexical_rows = (
            await self._session.scalars(
                select(KnowledgeChunkORM)
                .where(
                    KnowledgeChunkORM.goal_id == goal_id,
                    KnowledgeChunkORM.search_vector.op("@@")(ts_query),
                )
                .order_by(func.ts_rank_cd(KnowledgeChunkORM.search_vector, ts_query).desc())
                .limit(candidate_limit)
            )
        ).all()
        semantic_rows = (
            await self._session.scalars(
                select(KnowledgeChunkORM)
                .where(
                    KnowledgeChunkORM.goal_id == goal_id,
                    KnowledgeChunkORM.embedding.is_not(None),
                )
                .order_by(KnowledgeChunkORM.embedding.cosine_distance(query_embedding))
                .limit(candidate_limit)
            )
        ).all()
        by_id = {row.id: row for row in (*lexical_rows, *semantic_rows)}
        fused_ids = reciprocal_rank_fusion(
            [row.id for row in lexical_rows],
            [row.id for row in semantic_rows],
            limit=limit,
        )
        return [self._chunk_to_domain(by_id[item_id]) for item_id in fused_ids]

    @staticmethod
    def _source_to_domain(row: KnowledgeSourceORM) -> KnowledgeSource:
        return KnowledgeSource(
            id=row.id,
            user_id=row.user_id,
            goal_id=row.goal_id,
            source_type=KnowledgeSourceType(row.source_type),
            title=row.title,
            source_uri=row.source_uri,
            content_hash=row.content_hash,
            ingestion_status=KnowledgeIngestionStatus(row.ingestion_status),
            chunk_count=row.chunk_count,
            provenance_metadata=dict(row.provenance_metadata),
            error_detail=row.error_detail,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _chunk_to_domain(row: KnowledgeChunkORM) -> KnowledgeChunk:
        return KnowledgeChunk(
            id=row.id,
            source_id=row.source_id,
            goal_id=row.goal_id,
            chunk_index=row.chunk_index,
            section_title=row.section_title,
            page_number=row.page_number,
            content=row.content,
            token_count=row.token_count,
            embedding=tuple(row.embedding) if row.embedding is not None else None,
            provenance_json=dict(row.provenance_json),
            created_at=row.created_at,
        )
