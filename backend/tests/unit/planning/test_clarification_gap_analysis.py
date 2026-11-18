from datetime import UTC, date, datetime

from src.planning.application.services.clarification_gap_analysis import (
    FactProvenance,
    GapStatus,
    GoalFactProvenance,
    InformationGapAnalyzer,
)
from src.planning.domain.models.goal import Goal


def _goal(*, description: str = "", target_date: date | None = None) -> Goal:
    now = datetime(2026, 11, 14, tzinfo=UTC)
    return Goal(
        title="Học JavaScript",
        raw_description=description,
        target_date=target_date,
        prior_knowledge_level="BEGINNER",
        created_at=now,
        updated_at=now,
    )


def test_system_default_deadline_is_assumed_not_known() -> None:
    facts = InformationGapAnalyzer().analyze(
        goal=_goal(target_date=date(2027, 2, 6)),
        provenance=GoalFactProvenance(
            target_date=FactProvenance.SYSTEM_DEFAULT,
            prior_knowledge_level=FactProvenance.SYSTEM_DEFAULT,
            weekly_commitment_hours=FactProvenance.SYSTEM_DEFAULT,
        ),
        weekly_commitment_hours=12,
        availability_weekly_minutes=720,
    )

    timeline = next(item for item in facts if item.dimension == "TIMELINE")
    assert timeline.status is GapStatus.ASSUMED


def test_explicit_deadline_is_known() -> None:
    facts = InformationGapAnalyzer().analyze(
        goal=_goal(target_date=date(2027, 2, 6)),
        provenance=GoalFactProvenance(
            target_date=FactProvenance.USER_EXPLICIT,
            prior_knowledge_level=FactProvenance.USER_CONFIRMED,
            weekly_commitment_hours=FactProvenance.USER_CONFIRMED,
        ),
        weekly_commitment_hours=12,
        availability_weekly_minutes=720,
    )

    timeline = next(item for item in facts if item.dimension == "TIMELINE")
    assert timeline.status is GapStatus.KNOWN


def test_prior_exposure_mention_does_not_imply_complete_knowledge() -> None:
    facts = InformationGapAnalyzer().analyze(
        goal=_goal(description="Tôi từng học JavaScript nhưng đã quên gần hết."),
        provenance=GoalFactProvenance(
            target_date=FactProvenance.SYSTEM_DEFAULT,
            prior_knowledge_level=FactProvenance.SYSTEM_DEFAULT,
            weekly_commitment_hours=FactProvenance.USER_EXPLICIT,
        ),
        weekly_commitment_hours=8,
        availability_weekly_minutes=600,
    )

    prior = next(item for item in facts if item.dimension == "PRIOR_KNOWLEDGE")
    assert prior.status is GapStatus.PARTIAL


def test_commitment_above_observed_availability_is_contradictory() -> None:
    facts = InformationGapAnalyzer().analyze(
        goal=_goal(),
        provenance=GoalFactProvenance(
            target_date=FactProvenance.USER_CONFIRMED,
            prior_knowledge_level=FactProvenance.USER_CONFIRMED,
            weekly_commitment_hours=FactProvenance.USER_EXPLICIT,
        ),
        weekly_commitment_hours=20,
        availability_weekly_minutes=8 * 60,
    )

    commitment = next(item for item in facts if item.dimension == "TIME_COMMITMENT")
    assert commitment.status is GapStatus.CONTRADICTORY
    assert commitment.warning_code == "CONSTRAINT_CONFLICT"


def test_keyword_hint_alone_does_not_promote_preference_to_known() -> None:
    facts = InformationGapAnalyzer().analyze(
        goal=_goal(description="Tôi thích học qua thực hành."),
        provenance=GoalFactProvenance(),
        weekly_commitment_hours=None,
        availability_weekly_minutes=None,
    )

    preference = next(item for item in facts if item.dimension == "LEARNING_PREFERENCE")
    assert preference.status is GapStatus.PARTIAL


def test_confirmed_learner_memory_promotes_observed_dimension() -> None:
    facts = InformationGapAnalyzer().analyze(
        goal=_goal(),
        provenance=GoalFactProvenance(),
        weekly_commitment_hours=None,
        availability_weekly_minutes=None,
        observed_dimensions={"PRACTICAL_EXPERIENCE"},
    )

    experience = next(item for item in facts if item.dimension == "PRACTICAL_EXPERIENCE")
    assert experience.status is GapStatus.KNOWN
    assert experience.provenance is FactProvenance.SYSTEM_OBSERVED
