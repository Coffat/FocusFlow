from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from src.planning.domain.events.planning_events import OfficialScheduleAppliedEvent
from src.planning.domain.exceptions.planning_exceptions import PlanningDomainError
from src.shared_kernel.domain.base import AggregateRoot, generate_uuid7


class ScheduleProposalStatus(StrEnum):
    DRAFT = "DRAFT"
    APPLIED = "APPLIED"
    DISCARDED = "DISCARDED"


class ScheduleProposalType(StrEnum):
    INITIAL_SCHEDULE = "INITIAL_SCHEDULE"
    AI_RECOVERY = "AI_RECOVERY"
    POST_FAILURE_RESET = "POST_FAILURE_RESET"
    SCHEDULE_ONLY_REOPTIMIZE = "SCHEDULE_ONLY_REOPTIMIZE"
    WHAT_IF_SIMULATION = "WHAT_IF_SIMULATION"


@dataclass
class OfficialSchedule(AggregateRoot):
    """OfficialSchedule aggregate root representing the active committed study schedule (UC-08 / UC-12)."""

    roadmap_id: UUID = field(default_factory=generate_uuid7)
    total_sessions: int = 0
    total_planned_minutes: int = 0
    activated_at: datetime = field(default_factory=lambda: datetime.min)
    created_at: datetime = field(default_factory=lambda: datetime.min)
    updated_at: datetime = field(default_factory=lambda: datetime.min)

    def __post_init__(self) -> None:
        if self.total_sessions < 0:
            raise PlanningDomainError(
                message="Tổng số phiên học (total_sessions) phải >= 0.",
                code="INVALID_OFFICIAL_SCHEDULE_SESSIONS",
            )
        if self.total_planned_minutes < 0:
            raise PlanningDomainError(
                message="Tổng số phút dự kiến (total_planned_minutes) phải >= 0.",
                code="INVALID_OFFICIAL_SCHEDULE_MINUTES",
            )
        if self.created_at == datetime.min and self.activated_at != datetime.min:
            self.created_at = self.activated_at

    def apply_metrics(
        self,
        *,
        user_id: UUID,
        total_sessions: int,
        total_planned_minutes: int,
        now: datetime,
        proposal_id: UUID | None = None,
    ) -> None:
        if total_sessions < 0 or total_planned_minutes < 0:
            raise PlanningDomainError(
                message="Thông số lịch chính thức không hợp lệ (âm).",
                code="INVALID_OFFICIAL_SCHEDULE_METRICS",
            )
        self.total_sessions = total_sessions
        self.total_planned_minutes = total_planned_minutes
        self.activated_at = now
        self.updated_at = now
        self.add_domain_event(
            OfficialScheduleAppliedEvent(
                aggregate_id=self.id,
                user_id=user_id,
                roadmap_id=self.roadmap_id,
                schedule_id=self.id,
                proposal_id=proposal_id,
                total_sessions=total_sessions,
                total_planned_minutes=total_planned_minutes,
                occurred_at=now,
            )
        )


@dataclass
class ScheduleProposal(AggregateRoot):
    """ScheduleProposal aggregate root holding a DRAFT/APPLIED/DISCARDED schedule proposal (BUSR-02)."""

    roadmap_id: UUID = field(default_factory=generate_uuid7)
    user_id: UUID = field(default_factory=generate_uuid7)
    proposal_data: dict[str, Any] = field(default_factory=dict)
    proposal_type: ScheduleProposalType = ScheduleProposalType.INITIAL_SCHEDULE
    original_proposal_data: dict[str, Any] = field(default_factory=dict)
    user_edit_count: int = 0
    pedagogical_warnings: list[dict[str, Any]] = field(default_factory=list)
    status: ScheduleProposalStatus = ScheduleProposalStatus.DRAFT
    applied_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.min)
    updated_at: datetime = field(default_factory=lambda: datetime.min)

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            self.status = ScheduleProposalStatus(self.status)
        if isinstance(self.proposal_type, str):
            self.proposal_type = ScheduleProposalType(self.proposal_type)
        if not isinstance(self.proposal_data, dict):
            raise PlanningDomainError(
                message="proposal_data phải là một dict JSON hợp lệ.",
                code="INVALID_PROPOSAL_DATA",
            )
        if self.user_edit_count < 0:
            raise PlanningDomainError(
                message="Số lần chỉnh sửa đề xuất không thể âm.",
                code="INVALID_PROPOSAL_EDIT_COUNT",
            )
        if self.updated_at == datetime.min and self.created_at != datetime.min:
            self.updated_at = self.created_at

    def mark_applied(self, now: datetime) -> None:
        if self.status != ScheduleProposalStatus.DRAFT:
            raise PlanningDomainError(
                message=f"Chỉ có thể áp dụng đề xuất ở trạng thái DRAFT (hiện tại: {self.status.value}).",
                code="INVALID_PROPOSAL_STATE_TRANSITION",
            )
        self.status = ScheduleProposalStatus.APPLIED
        self.applied_at = now
        self.updated_at = now

    def mark_discarded(self, now: datetime) -> None:
        if self.status != ScheduleProposalStatus.DRAFT:
            raise PlanningDomainError(
                message=f"Chỉ có thể hủy đề xuất ở trạng thái DRAFT (hiện tại: {self.status.value}).",
                code="INVALID_PROPOSAL_STATE_TRANSITION",
            )
        self.status = ScheduleProposalStatus.DISCARDED
        self.updated_at = now
