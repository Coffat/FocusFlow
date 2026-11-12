from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.account.domain.models.learner_memory import (
    InvalidLearnerMemoryError,
    LearnerConceptMastery,
    LearnerMemoryItem,
    MemoryCategory,
    MemoryEpistemicLevel,
    MemoryStatus,
)


def test_explicit_memory_is_always_confirmed() -> None:
    item = LearnerMemoryItem(
        user_id=uuid4(),
        memory_key="preferred.session_length",
        value={"minutes": 45},
        category=MemoryCategory.PREFERENCE,
        epistemic_level=MemoryEpistemicLevel.EXPLICIT,
        confidence=1,
        sample_size=1,
        evidence=(),
        status=MemoryStatus.CONFIRMED,
    )
    assert item.status is MemoryStatus.CONFIRMED


def test_inferred_memory_requires_threshold_and_seven_evidence_records() -> None:
    now = datetime.now(UTC)
    with pytest.raises(InvalidLearnerMemoryError):
        LearnerMemoryItem(
            user_id=uuid4(),
            memory_key="focus.peak",
            value={"period": "EVENING"},
            category=MemoryCategory.BEHAVIOR,
            epistemic_level=MemoryEpistemicLevel.INFERRED,
            confidence=0.69,
            sample_size=2,
            evidence=({},),
            observation_started_at=now - timedelta(days=7),
            observation_ended_at=now,
        )


def test_mastery_rejects_plain_task_completion() -> None:
    with pytest.raises(ValueError, match="not mastery evidence"):
        LearnerConceptMastery(
            user_id=uuid4(),
            concept_key="dag",
            mastery_score=0.5,
            evidence_count=1,
            last_evidence_type="TASK_COMPLETED",
        )
