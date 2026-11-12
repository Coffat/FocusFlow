from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class KnowledgeSourceType(StrEnum):
    PDF = "PDF"
    DOCX = "DOCX"
    TXT = "TXT"
    URL = "URL"


class KnowledgeIngestionStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True, slots=True)
class KnowledgeSource:
    id: UUID
    user_id: UUID
    goal_id: UUID
    source_type: KnowledgeSourceType
    title: str
    source_uri: str | None
    content_hash: str
    ingestion_status: KnowledgeIngestionStatus
    chunk_count: int
    provenance_metadata: dict[str, Any]
    error_detail: str | None
    created_at: datetime
    updated_at: datetime

    def mark_processing(self, *, now: datetime) -> "KnowledgeSource":
        return replace(self, ingestion_status=KnowledgeIngestionStatus.PROCESSING, updated_at=now)

    def mark_indexed(self, *, chunk_count: int, now: datetime) -> "KnowledgeSource":
        if chunk_count < 1:
            raise ValueError("Indexed knowledge source must contain at least one chunk")
        return replace(
            self,
            ingestion_status=KnowledgeIngestionStatus.INDEXED,
            chunk_count=chunk_count,
            error_detail=None,
            updated_at=now,
        )

    def mark_failed(self, *, detail: str, now: datetime) -> "KnowledgeSource":
        return replace(
            self,
            ingestion_status=KnowledgeIngestionStatus.FAILED,
            error_detail=detail[:2000],
            updated_at=now,
        )

    def quarantine(self, *, detail: str, now: datetime) -> "KnowledgeSource":
        return replace(
            self,
            ingestion_status=KnowledgeIngestionStatus.QUARANTINED,
            error_detail=detail[:2000],
            updated_at=now,
        )


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    id: UUID
    source_id: UUID
    goal_id: UUID
    chunk_index: int
    content: str
    token_count: int
    provenance_json: dict[str, Any]
    created_at: datetime
    section_title: str | None = None
    page_number: int | None = None
    embedding: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        if self.chunk_index < 0 or self.token_count < 1:
            raise ValueError("Invalid knowledge chunk bounds")
        if self.embedding is not None and len(self.embedding) != 768:
            raise ValueError("Knowledge chunk embedding must have 768 dimensions")
