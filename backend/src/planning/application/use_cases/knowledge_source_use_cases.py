import hashlib
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from uuid6 import uuid7

from src.planning.application.knowledge import DocumentExtractor, SafeUrlFetcher, SemanticChunker
from src.planning.application.ports.knowledge_file_store_port import KnowledgeFileStorePort
from src.planning.application.ports.knowledge_source_repository_port import (
    KnowledgeSourceRepositoryPort,
)
from src.planning.application.ports.planning_repository_ports import GoalRepositoryPort
from src.planning.domain.models.knowledge_source import (
    KnowledgeChunk,
    KnowledgeIngestionStatus,
    KnowledgeSource,
    KnowledgeSourceType,
)
from src.shared_kernel.application.embedding_port import EmbeddingProviderPort
from src.shared_kernel.application.uow import AsyncUnitOfWork


class KnowledgeSourceNotFoundError(LookupError):
    code = "KNOWLEDGE_SOURCE_NOT_FOUND"


class CreateKnowledgeSourceUseCase:
    def __init__(
        self,
        *,
        goal_repository: GoalRepositoryPort,
        source_repository: KnowledgeSourceRepositoryPort,
        file_store: KnowledgeFileStorePort,
        uow: AsyncUnitOfWork,
        max_file_bytes: int,
    ) -> None:
        self._goals = goal_repository
        self._sources = source_repository
        self._files = file_store
        self._uow = uow
        self._max_file_bytes = max_file_bytes

    async def create_file(
        self,
        *,
        user_id: UUID,
        goal_id: UUID,
        title: str,
        filename: str,
        content: bytes,
    ) -> KnowledgeSource:
        goal = await self._goals.get_by_id_for_user(goal_id, user_id)
        if goal is None:
            raise KnowledgeSourceNotFoundError("Goal not found")
        if not content or len(content) > self._max_file_bytes:
            raise ValueError("Tệp học liệu phải có dung lượng từ 1 byte đến 20 MB")
        suffix = Path(filename).suffix.lower().lstrip(".")
        try:
            source_type = KnowledgeSourceType(suffix.upper())
        except ValueError as exc:
            raise ValueError("Chỉ hỗ trợ tệp PDF, DOCX hoặc TXT") from exc
        now = datetime.now(UTC)
        source_id = uuid7()
        uri = await self._files.save(source_id, suffix, content)
        source = KnowledgeSource(
            id=source_id,
            user_id=user_id,
            goal_id=goal_id,
            source_type=source_type,
            title=title.strip() or filename,
            source_uri=uri,
            content_hash=hashlib.sha256(content).hexdigest(),
            ingestion_status=KnowledgeIngestionStatus.PENDING,
            chunk_count=0,
            provenance_metadata={"original_filename": Path(filename).name},
            error_detail=None,
            created_at=now,
            updated_at=now,
        )
        try:
            async with self._uow:
                saved = await self._sources.save_source(source)
                await self._uow.commit()
        except Exception:
            await self._files.delete(uri)
            raise
        return saved

    async def create_url(
        self, *, user_id: UUID, goal_id: UUID, title: str, url: str
    ) -> KnowledgeSource:
        goal = await self._goals.get_by_id_for_user(goal_id, user_id)
        if goal is None:
            raise KnowledgeSourceNotFoundError("Goal not found")
        normalized_url = url.strip()
        SafeUrlFetcher._validate_shape(normalized_url)
        now = datetime.now(UTC)
        source = KnowledgeSource(
            id=uuid7(),
            user_id=user_id,
            goal_id=goal_id,
            source_type=KnowledgeSourceType.URL,
            title=title.strip() or "Nguồn học liệu URL",
            source_uri=normalized_url,
            content_hash=hashlib.sha256(normalized_url.encode()).hexdigest(),
            ingestion_status=KnowledgeIngestionStatus.PENDING,
            chunk_count=0,
            provenance_metadata={},
            error_detail=None,
            created_at=now,
            updated_at=now,
        )
        async with self._uow:
            saved = await self._sources.save_source(source)
            await self._uow.commit()
        return saved


class IngestKnowledgeSourceUseCase:
    def __init__(
        self,
        *,
        source_repository: KnowledgeSourceRepositoryPort,
        file_store: KnowledgeFileStorePort,
        embedding_provider: EmbeddingProviderPort,
        url_fetcher: SafeUrlFetcher,
        extractor: DocumentExtractor,
        chunker: SemanticChunker,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._sources = source_repository
        self._files = file_store
        self._embeddings = embedding_provider
        self._fetcher = url_fetcher
        self._extractor = extractor
        self._chunker = chunker
        self._uow = uow

    async def execute(self, *, source_id: UUID, user_id: UUID) -> KnowledgeSource:
        source = await self._sources.get_source_for_user(source_id, user_id)
        if source is None:
            raise KnowledgeSourceNotFoundError("Knowledge source not found")
        now = datetime.now(UTC)
        async with self._uow:
            await self._sources.save_source(source.mark_processing(now=now))
            await self._uow.commit()
        try:
            if source.source_type is KnowledgeSourceType.URL:
                fetched = await self._fetcher.fetch(source.source_uri or "")
                content = fetched.content
                content_hash = hashlib.sha256(content).hexdigest()
                detected = self._detect_url_type(fetched.content_type, fetched.final_url)
                provenance = {"final_url": fetched.final_url, "content_type": fetched.content_type}
            else:
                content = await self._files.read(source.source_uri or "")
                content_hash = source.content_hash
                detected = source.source_type
                provenance = dict(source.provenance_metadata)
            sections = await self._extractor.extract(content, detected)
            semantic_chunks = self._chunker.chunk(sections)
            if not semantic_chunks:
                raise ValueError("Không trích xuất được nội dung văn bản từ học liệu")
            embeddings = await self._embeddings.embed([item.content for item in semantic_chunks])
            created_at = datetime.now(UTC)
            chunks = [
                KnowledgeChunk(
                    id=uuid7(),
                    source_id=source.id,
                    goal_id=source.goal_id,
                    chunk_index=index,
                    section_title=item.section_title,
                    page_number=item.page_number,
                    content=item.content,
                    token_count=item.token_count,
                    embedding=tuple(embeddings[index]),
                    provenance_json={
                        **provenance,
                        "source_id": str(source.id),
                        "source_title": source.title,
                        "chunk_index": index,
                    },
                    created_at=created_at,
                )
                for index, item in enumerate(semantic_chunks)
            ]
            indexed = replace(
                source,
                content_hash=content_hash,
                provenance_metadata=provenance,
            ).mark_indexed(chunk_count=len(chunks), now=created_at)
            async with self._uow:
                await self._sources.replace_chunks(source.id, chunks)
                saved = await self._sources.save_source(indexed)
                await self._uow.commit()
            return saved
        except Exception as exc:
            status_source = (
                source.quarantine(detail=str(exc), now=datetime.now(UTC))
                if getattr(exc, "code", "") == "KNOWLEDGE_SOURCE_QUARANTINED"
                else source.mark_failed(detail=str(exc), now=datetime.now(UTC))
            )
            async with self._uow:
                await self._sources.save_source(status_source)
                await self._uow.commit()
            raise

    @staticmethod
    def _detect_url_type(content_type: str, url: str) -> KnowledgeSourceType:
        lowered = content_type.lower()
        suffix = Path(url.split("?", maxsplit=1)[0]).suffix.lower()
        if "pdf" in lowered or suffix == ".pdf":
            return KnowledgeSourceType.PDF
        if "wordprocessingml" in lowered or suffix == ".docx":
            return KnowledgeSourceType.DOCX
        return KnowledgeSourceType.TXT
