from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from src.shared_kernel.domain.base import generate_uuid7, utc_now


class MemoryEpistemicLevel(StrEnum):
    EXPLICIT = "EXPLICIT"
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"


class MemoryStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class MemoryCategory(StrEnum):
    PREFERENCE = "PREFERENCE"
    BEHAVIOR = "BEHAVIOR"
    KNOWLEDGE = "KNOWLEDGE"
    INTERACTION = "INTERACTION"


class InvalidLearnerMemoryError(ValueError):
    pass


@dataclass(frozen=True)
class LearnerMemoryItem:
    user_id: UUID
    memory_key: str
    value: dict[str, Any]
    category: MemoryCategory
    epistemic_level: MemoryEpistemicLevel
    confidence: float
    sample_size: int
    evidence: tuple[dict[str, Any], ...]
    observation_started_at: datetime | None = None
    observation_ended_at: datetime | None = None
    status: MemoryStatus = MemoryStatus.PENDING
    id: UUID = field(default_factory=generate_uuid7)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.memory_key.strip():
            raise InvalidLearnerMemoryError("memory_key is required")
        if not 0 <= self.confidence <= 1:
            raise InvalidLearnerMemoryError("confidence must be between 0 and 1")
        if self.sample_size < 0:
            raise InvalidLearnerMemoryError("sample_size cannot be negative")
        if self.epistemic_level is MemoryEpistemicLevel.EXPLICIT:
            if self.status is not MemoryStatus.CONFIRMED or self.confidence != 1:
                raise InvalidLearnerMemoryError(
                    "explicit memory must be confirmed with confidence 1"
                )
        if self.epistemic_level is MemoryEpistemicLevel.INFERRED:
            if self.sample_size < 3 or self.confidence < 0.7:
                raise InvalidLearnerMemoryError(
                    "inferred memory requires sample_size >= 3 and confidence >= 0.7"
                )
            if self.observation_started_at is None or self.observation_ended_at is None:
                raise InvalidLearnerMemoryError("inferred memory requires an observation window")
            if len(self.evidence) < 7:
                raise InvalidLearnerMemoryError("inferred memory requires seven evidence records")

    def confirm(self) -> "LearnerMemoryItem":
        return replace(self, status=MemoryStatus.CONFIRMED, updated_at=utc_now())

    def reject(self) -> "LearnerMemoryItem":
        return replace(self, status=MemoryStatus.REJECTED, updated_at=utc_now())

    def edit(self, value: dict[str, Any]) -> "LearnerMemoryItem":
        if not value:
            raise InvalidLearnerMemoryError("memory value cannot be empty")
        return replace(
            self,
            value=value,
            epistemic_level=MemoryEpistemicLevel.EXPLICIT,
            confidence=1,
            status=MemoryStatus.CONFIRMED,
            updated_at=utc_now(),
        )


@dataclass(frozen=True)
class LearnerConceptMastery:
    user_id: UUID
    concept_key: str
    mastery_score: float
    evidence_count: int
    last_evidence_type: str
    id: UUID = field(default_factory=generate_uuid7)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not 0 <= self.mastery_score <= 1:
            raise ValueError("mastery_score must be between 0 and 1")
        if self.evidence_count < 1:
            raise ValueError("mastery requires evidence")
        if self.last_evidence_type not in {"PROVE_MODE", "EVIDENCED_TAKEAWAY"}:
            raise ValueError("task completion is not mastery evidence")
