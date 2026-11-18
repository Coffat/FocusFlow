from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from src.planning.application.dtos.planning_dtos import (
    DiagnosticDimension,
    normalize_diagnostic_dimension,
)
from src.planning.domain.models.goal import Goal


class FactProvenance(StrEnum):
    USER_CONFIRMED = "USER_CONFIRMED"
    USER_EXPLICIT = "USER_EXPLICIT"
    SYSTEM_OBSERVED = "SYSTEM_OBSERVED"
    SYSTEM_DEFAULT = "SYSTEM_DEFAULT"
    AI_INFERRED = "AI_INFERRED"


class GapStatus(StrEnum):
    KNOWN = "KNOWN"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    CONTRADICTORY = "CONTRADICTORY"
    ASSUMED = "ASSUMED"


class ClarificationSessionStatus(StrEnum):
    ANALYZING = "ANALYZING"
    WAITING_ANSWER = "WAITING_ANSWER"
    WAITING_FOLLOW_UP = "WAITING_FOLLOW_UP"
    READY_TO_PLAN = "READY_TO_PLAN"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class GoalFactProvenance:
    target_date: FactProvenance = FactProvenance.SYSTEM_DEFAULT
    prior_knowledge_level: FactProvenance = FactProvenance.SYSTEM_DEFAULT
    weekly_commitment_hours: FactProvenance = FactProvenance.SYSTEM_DEFAULT

    @classmethod
    def from_mapping(cls, raw: dict[str, Any] | None) -> GoalFactProvenance:
        values = raw or {}

        def parse(field: str) -> FactProvenance:
            try:
                return FactProvenance(str(values.get(field, FactProvenance.SYSTEM_DEFAULT)))
            except ValueError:
                return FactProvenance.SYSTEM_DEFAULT

        return cls(
            target_date=parse("target_date"),
            prior_knowledge_level=parse("prior_knowledge_level"),
            weekly_commitment_hours=parse("weekly_commitment_hours"),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "target_date": self.target_date.value,
            "prior_knowledge_level": self.prior_knowledge_level.value,
            "weekly_commitment_hours": self.weekly_commitment_hours.value,
        }


@dataclass(frozen=True, slots=True)
class InformationGap:
    dimension: str
    status: GapStatus
    provenance: FactProvenance
    value: Any = None
    priority: int = 0
    roadmap_decision: str = ""
    evidence: tuple[str, ...] = ()
    warning_code: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "status": self.status.value,
            "provenance": self.provenance.value,
            "value": self.value,
            "priority": self.priority,
            "roadmap_decision": self.roadmap_decision,
            "evidence": list(self.evidence),
            "warning_code": self.warning_code,
        }


class FactNormalizer:
    """Normalize structured learner facts without promoting keyword hits to known facts."""

    @staticmethod
    def has_specific_outcome(goal: Goal) -> bool:
        text = f"{goal.title} {goal.raw_description or ''}".lower()
        return any(
            marker in text
            for marker in (
                "chứng chỉ",
                "thi ",
                "dự án",
                "project",
                "phỏng vấn",
                "interview",
                "xây dựng",
                "đạt ",
                "ielts",
            )
        )

    @staticmethod
    def prior_knowledge_detail(goal: Goal) -> GapStatus:
        text = (goal.raw_description or "").lower()
        if not text.strip():
            return GapStatus.UNKNOWN
        uncertainty_markers = (
            "quên gần hết",
            "không chắc",
            "mơ hồ",
            "chưa rõ",
            "học qua",
            "từng học",
        )
        if any(marker in text for marker in uncertainty_markers):
            return GapStatus.PARTIAL
        concrete_markers = (
            "năm kinh nghiệm",
            "đã làm",
            "đã xây dựng",
            "thành thạo",
            "đã hoàn thành",
            "chưa từng",
            "mới bắt đầu",
        )
        if any(marker in text for marker in concrete_markers):
            return GapStatus.KNOWN
        return GapStatus.UNKNOWN

    @staticmethod
    def desired_depth(goal: Goal) -> GapStatus:
        text = f"{goal.title} {goal.raw_description or ''}".lower()
        if any(
            marker in text
            for marker in (
                "cơ bản",
                "nhập môn",
                "chuyên sâu",
                "production",
                "nâng cao",
                "thành thạo",
            )
        ):
            return GapStatus.PARTIAL
        return GapStatus.UNKNOWN

    @staticmethod
    def learning_preference(goal: Goal) -> GapStatus:
        text = (goal.raw_description or "").lower()
        if any(
            marker in text
            for marker in (
                "thực hành",
                "lý thuyết",
                "video",
                "đọc tài liệu",
                "làm bài tập",
                "làm dự án",
            )
        ):
            return GapStatus.PARTIAL
        return GapStatus.UNKNOWN


class InformationGapAnalyzer:
    """Deterministic, provenance-aware gap analysis for goal clarification."""

    def analyze(
        self,
        *,
        goal: Goal,
        provenance: GoalFactProvenance,
        weekly_commitment_hours: float | None,
        availability_weekly_minutes: int | None,
        observed_dimensions: set[str] | None = None,
    ) -> list[InformationGap]:
        observed = {normalize_diagnostic_dimension(d) for d in (observed_dimensions or set())}
        prior_detail = FactNormalizer.prior_knowledge_detail(goal)
        if provenance.prior_knowledge_level in (
            FactProvenance.USER_EXPLICIT,
            FactProvenance.USER_CONFIRMED,
        ):
            prior_status = GapStatus.KNOWN if prior_detail is GapStatus.KNOWN else GapStatus.PARTIAL
        elif prior_detail is not GapStatus.UNKNOWN:
            prior_status = prior_detail
        else:
            prior_status = GapStatus.ASSUMED

        timeline_status = self._status_from_provenance(
            has_value=goal.target_date is not None,
            provenance=provenance.target_date,
        )
        commitment_status = self._status_from_provenance(
            has_value=weekly_commitment_hours is not None,
            provenance=provenance.weekly_commitment_hours,
        )
        commitment_warning: str | None = None
        commitment_evidence: tuple[str, ...] = ()
        if weekly_commitment_hours is not None and availability_weekly_minutes is not None:
            requested_minutes = int(weekly_commitment_hours * 60)
            commitment_evidence = (
                f"requested_minutes={requested_minutes}",
                f"observed_available_minutes={availability_weekly_minutes}",
            )
            if requested_minutes > availability_weekly_minutes:
                commitment_status = GapStatus.CONTRADICTORY
                commitment_warning = "CONSTRAINT_CONFLICT"

        outcome_status = GapStatus.UNKNOWN
        if FactNormalizer.has_specific_outcome(goal):
            outcome_status = (
                GapStatus.KNOWN
                if len((goal.raw_description or "").strip()) >= 30
                else GapStatus.PARTIAL
            )
        depth_status = FactNormalizer.desired_depth(goal)
        preference_status = FactNormalizer.learning_preference(goal)
        practical_status = (
            GapStatus.PARTIAL
            if prior_status in (GapStatus.KNOWN, GapStatus.PARTIAL)
            else GapStatus.UNKNOWN
        )

        if DiagnosticDimension.PRIOR_KNOWLEDGE.value in observed:
            prior_status = GapStatus.KNOWN
        if DiagnosticDimension.PRACTICAL_EXPERIENCE.value in observed:
            practical_status = GapStatus.KNOWN
        if DiagnosticDimension.DESIRED_DEPTH.value in observed:
            depth_status = GapStatus.KNOWN
        if DiagnosticDimension.LEARNING_PREFERENCE.value in observed:
            preference_status = GapStatus.KNOWN

        gaps = [
            InformationGap(
                dimension=DiagnosticDimension.TARGET_OUTCOME.value,
                status=outcome_status,
                provenance=FactProvenance.USER_EXPLICIT,
                value=goal.title,
                priority=100,
                roadmap_decision="Phạm vi và tiêu chí hoàn thành của Roadmap",
            ),
            InformationGap(
                dimension=DiagnosticDimension.PRIOR_KNOWLEDGE.value,
                status=prior_status,
                provenance=(
                    FactProvenance.SYSTEM_OBSERVED
                    if DiagnosticDimension.PRIOR_KNOWLEDGE.value in observed
                    else provenance.prior_knowledge_level
                ),
                value=goal.prior_knowledge_level,
                priority=95,
                roadmap_decision="Điểm bắt đầu và nội dung được phép lược bỏ",
            ),
            InformationGap(
                dimension=DiagnosticDimension.PRACTICAL_EXPERIENCE.value,
                status=practical_status,
                provenance=(
                    FactProvenance.SYSTEM_OBSERVED
                    if DiagnosticDimension.PRACTICAL_EXPERIENCE.value in observed
                    else FactProvenance.AI_INFERRED
                ),
                priority=75,
                roadmap_decision="Độ khó và loại bài tập thực hành",
            ),
            InformationGap(
                dimension=DiagnosticDimension.TIME_COMMITMENT.value,
                status=commitment_status,
                provenance=provenance.weekly_commitment_hours,
                value=weekly_commitment_hours,
                priority=90,
                roadmap_decision="Nhịp học và mật độ task theo tuần",
                evidence=commitment_evidence,
                warning_code=commitment_warning,
            ),
            InformationGap(
                dimension=DiagnosticDimension.TIMELINE.value,
                status=timeline_status,
                provenance=provenance.target_date,
                value=goal.target_date.isoformat() if goal.target_date else None,
                priority=85,
                roadmap_decision="Phạm vi và thứ tự ưu tiên theo hạn chót",
            ),
            InformationGap(
                dimension=DiagnosticDimension.DESIRED_DEPTH.value,
                status=depth_status,
                provenance=(
                    FactProvenance.SYSTEM_OBSERVED
                    if DiagnosticDimension.DESIRED_DEPTH.value in observed
                    else FactProvenance.USER_EXPLICIT
                ),
                priority=80,
                roadmap_decision="Độ sâu kỹ thuật của Milestone và Task",
            ),
            InformationGap(
                dimension=DiagnosticDimension.LEARNING_PREFERENCE.value,
                status=preference_status,
                provenance=(
                    FactProvenance.SYSTEM_OBSERVED
                    if DiagnosticDimension.LEARNING_PREFERENCE.value in observed
                    else FactProvenance.USER_EXPLICIT
                ),
                priority=40,
                roadmap_decision="Tỷ lệ lý thuyết, thực hành và ôn tập",
            ),
        ]
        return gaps

    @staticmethod
    def _status_from_provenance(*, has_value: bool, provenance: FactProvenance) -> GapStatus:
        if not has_value:
            return GapStatus.UNKNOWN
        if provenance in (
            FactProvenance.USER_CONFIRMED,
            FactProvenance.USER_EXPLICIT,
            FactProvenance.SYSTEM_OBSERVED,
        ):
            return GapStatus.KNOWN
        return GapStatus.ASSUMED

    @staticmethod
    def select_question_gaps(gaps: list[InformationGap], *, limit: int = 3) -> list[InformationGap]:
        open_statuses = {
            GapStatus.PARTIAL,
            GapStatus.UNKNOWN,
            GapStatus.CONTRADICTORY,
            GapStatus.ASSUMED,
        }
        return sorted(
            (gap for gap in gaps if gap.status in open_statuses),
            key=lambda item: item.priority,
            reverse=True,
        )[: max(0, limit)]
