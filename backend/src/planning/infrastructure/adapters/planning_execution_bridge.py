from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from src.account.public_api import (
    create_availability_query_port,
    create_calendar_connection_query_port,
    create_user_query_port,
)
from src.execution.public_api import (
    ExistingScheduledTaskDTO,
    create_execution_schedule_sync_port,
)
from src.planning.application.services.effective_availability_service import (
    GetEffectiveAvailabilityUseCase,
)
from src.planning.application.services.existing_schedule_occupancy import (
    expand_existing_schedule_occupancy,
)
from src.planning.domain.exceptions.planning_exceptions import (
    RescheduleBudgetExhaustedError,
    RoadmapNotFoundError,
    RoadmapReadOnlyError,
)
from src.planning.domain.models.schedule_block import ScheduleBlock
from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
from src.planning.domain.services.validation_types import (
    SoftOverflowWarningDTO,
    parse_iso_datetime,
)
from src.planning.infrastructure.orm.planning_orm import (
    MilestoneORM,
    OfficialScheduleORM,
    RoadmapORM,
    ScheduleBlockORM,
)
from src.planning.public_api import (
    ExecutionWeekScheduleBlockDTO,
    ManualSlotValidationResultDTO,
    MilestoneExecutionContextDTO,
    PlanningExecutionBridgePort,
    RoadmapExecutionContextDTO,
    register_planning_execution_bridge_factory,
)

_READ_ONLY_ROADMAP_STATUSES = frozenset({"COMPLETED", "ARCHIVED"})


def _resolve_tz(tz_name: str | None) -> ZoneInfo:
    raw = (tz_name or "").strip()
    if not raw:
        return ZoneInfo("Asia/Ho_Chi_Minh")
    try:
        return ZoneInfo(raw)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _to_schedule_block_domain(orm: ScheduleBlockORM) -> ScheduleBlock:
    return ScheduleBlock(
        id=orm.id,
        roadmap_id=orm.roadmap_id,
        official_schedule_id=orm.official_schedule_id,
        task_id=orm.task_id,
        sequence_in_task=orm.sequence_in_task,
        block_type=orm.block_type,
        block_date=orm.block_date,
        start_time=orm.start_time,
        end_time=orm.end_time,
        scheduled_duration_minutes=orm.scheduled_duration_minutes,
        is_protected=orm.is_protected,
        status=orm.status,
        external_calendar_event_id=orm.external_calendar_event_id,
        etag=orm.etag,
        sync_status=orm.sync_status,
        last_synced_at=orm.last_synced_at,
        placement_rationale=orm.placement_rationale,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class PlanningExecutionBridgeAdapter(PlanningExecutionBridgePort):
    """Cross-context bridge from Planning to Execution (add/flush only, never commit)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_roadmaps_context(
        self,
        user_id: UUID,
        roadmap_id: UUID | None = None,
    ) -> list[RoadmapExecutionContextDTO]:
        stmt = select(RoadmapORM).where(RoadmapORM.user_id == user_id)
        if roadmap_id is not None:
            stmt = stmt.where(RoadmapORM.id == roadmap_id)
        stmt = stmt.order_by(RoadmapORM.created_at.asc())
        roadmaps = list((await self._session.execute(stmt)).scalars().all())
        if not roadmaps:
            return []

        rids = [r.id for r in roadmaps]
        sched_stmt = select(OfficialScheduleORM.roadmap_id, OfficialScheduleORM.id).where(
            OfficialScheduleORM.roadmap_id.in_(rids)
        )
        sched_map = {row[0]: row[1] for row in (await self._session.execute(sched_stmt)).fetchall()}

        return [
            RoadmapExecutionContextDTO(
                roadmap_id=r.id,
                user_id=r.user_id,
                title=r.title,
                status=r.status,
                target_date=r.target_date,
                official_schedule_id=sched_map.get(r.id),
                weekly_reschedule_budget=int(r.weekly_reschedule_budget),
                weekly_reschedule_used=int(r.weekly_reschedule_used),
                budget_week_start=r.budget_week_start,
            )
            for r in roadmaps
        ]

    async def get_milestone_sequences(
        self,
        roadmap_ids: Sequence[UUID],
    ) -> dict[UUID, int]:
        if not roadmap_ids:
            return {}
        stmt = select(MilestoneORM.id, MilestoneORM.sequence_order).where(
            MilestoneORM.roadmap_id.in_(list(roadmap_ids))
        )
        rows = (await self._session.execute(stmt)).fetchall()
        return {row[0]: int(row[1]) for row in rows}

    async def get_milestones_context(
        self,
        roadmap_ids: Sequence[UUID],
    ) -> dict[UUID, MilestoneExecutionContextDTO]:
        if not roadmap_ids:
            return {}
        stmt = select(MilestoneORM).where(MilestoneORM.roadmap_id.in_(list(roadmap_ids)))
        rows = list((await self._session.execute(stmt)).scalars().all())
        return {
            m.id: MilestoneExecutionContextDTO(
                milestone_id=m.id,
                roadmap_id=m.roadmap_id,
                sequence_order=int(m.sequence_order),
                title=m.title,
                learning_outcomes=tuple(str(item) for item in (m.learning_outcomes or [])),
                completion_criteria=m.completion_criteria,
            )
            for m in rows
        }

    async def verify_milestone_in_roadmap(
        self,
        user_id: UUID,
        roadmap_id: UUID,
        milestone_id: UUID,
    ) -> bool:
        stmt = (
            select(MilestoneORM.id)
            .join(RoadmapORM, RoadmapORM.id == MilestoneORM.roadmap_id)
            .where(
                MilestoneORM.id == milestone_id,
                MilestoneORM.roadmap_id == roadmap_id,
                RoadmapORM.user_id == user_id,
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def get_week_schedule_blocks(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[ExecutionWeekScheduleBlockDTO]:
        stmt = (
            select(ScheduleBlockORM, RoadmapORM.title, RoadmapORM.status)
            .join(RoadmapORM, RoadmapORM.id == ScheduleBlockORM.roadmap_id)
            .where(
                RoadmapORM.user_id == user_id,
                ScheduleBlockORM.block_date >= start_date,
                ScheduleBlockORM.block_date <= end_date,
                ScheduleBlockORM.status != "CANCELLED",
            )
            .order_by(
                ScheduleBlockORM.block_date.asc(),
                ScheduleBlockORM.start_time.asc(),
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            ExecutionWeekScheduleBlockDTO(
                id=block.id,
                roadmap_id=block.roadmap_id,
                roadmap_title=roadmap_title,
                roadmap_status=roadmap_status,
                official_schedule_id=block.official_schedule_id,
                task_id=block.task_id,
                sequence_in_task=block.sequence_in_task,
                block_type=block.block_type,
                block_date=block.block_date,
                start_time=block.start_time,
                end_time=block.end_time,
                scheduled_duration_minutes=block.scheduled_duration_minutes,
                is_protected=block.is_protected,
                status=block.status,
                sync_status=block.sync_status,
                placement_rationale=block.placement_rationale,
            )
            for block, roadmap_title, roadmap_status in rows
        ]

    async def verify_roadmap_writable(
        self,
        user_id: UUID,
        roadmap_id: UUID,
    ) -> date | None:
        stmt = select(RoadmapORM).where(
            RoadmapORM.id == roadmap_id,
            RoadmapORM.user_id == user_id,
        )
        roadmap = (await self._session.execute(stmt)).scalar_one_or_none()
        if roadmap is None:
            raise RoadmapNotFoundError(roadmap_id)
        if roadmap.status in _READ_ONLY_ROADMAP_STATUSES:
            raise RoadmapReadOnlyError()
        return roadmap.target_date

    async def validate_manual_task_slot(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        task_id: UUID | None,
        scheduled_date: date,
        scheduled_start: datetime | None,
        scheduled_end: datetime | None,
        estimated_minutes: int,
        confirm_soft_overflow: bool = False,
    ) -> ManualSlotValidationResultDTO:
        target_date = await self.verify_roadmap_writable(user_id, roadmap_id)

        user_tz_name = "Asia/Ho_Chi_Minh"
        user_snap = await create_user_query_port(self._session).get_user_by_id(user_id)
        if user_snap is not None and user_snap.timezone:
            user_tz_name = user_snap.timezone

        # Load official_schedule_id for target roadmap
        sched_stmt = select(OfficialScheduleORM.id).where(
            OfficialScheduleORM.roadmap_id == roadmap_id
        )
        official_schedule_id = (await self._session.execute(sched_stmt)).scalar_one_or_none()

        # Load all active roadmaps + target roadmap for occupancy calculation
        rm_stmt = select(RoadmapORM).where(
            RoadmapORM.user_id == user_id,
            RoadmapORM.status == "ACTIVE",
        )
        active_roadmaps = list((await self._session.execute(rm_stmt)).scalars().all())
        roadmap_ids_for_occupancy = list({*(r.id for r in active_roadmaps), roadmap_id})
        target_dates_map = {r.id: r.target_date for r in active_roadmaps}
        target_dates_map[roadmap_id] = target_date

        exec_sync = create_execution_schedule_sync_port(self._session)
        raw_existing_tasks = await exec_sync.get_tasks_for_roadmaps(
            roadmap_ids_for_occupancy,
            roadmap_target_dates=target_dates_map,
        )
        # Exclude the task being edited/rescheduled so it doesn't conflict with itself
        filtered_tasks: list[ExistingScheduledTaskDTO] = [
            t for t in raw_existing_tasks if task_id is None or t.task_id != task_id
        ]

        block_stmt = select(ScheduleBlockORM).where(
            ScheduleBlockORM.roadmap_id.in_(roadmap_ids_for_occupancy),
            ScheduleBlockORM.status == "PLANNED",
        )
        raw_blocks = list((await self._session.execute(block_stmt)).scalars().all())
        filtered_blocks = [
            _to_schedule_block_domain(b)
            for b in raw_blocks
            if task_id is None or b.task_id != task_id
        ]
        existing_tasks = expand_existing_schedule_occupancy(filtered_tasks, filtered_blocks)

        avail_port = create_availability_query_port(self._session)
        cal_port = create_calendar_connection_query_port(self._session)
        effective_avail_uc = GetEffectiveAvailabilityUseCase(
            availability_query_port=avail_port,
            calendar_connection_query_port=cal_port,
            execution_sync_port=exec_sync,
        )
        effective_avail = await effective_avail_uc.execute(
            user_id=user_id,
            start_date=scheduled_date,
            target_date=scheduled_date,
            timezone=user_tz_name,
            existing_tasks=existing_tasks,
            exclude_roadmap_id=roadmap_id,
        )
        avail_config = effective_avail.availability_config
        effective_existing = list(effective_avail.effective_existing_tasks)

        candidate_task: dict[str, object] = {
            "task_id": str(task_id) if task_id is not None else "manual_candidate",
            "title": "Nhiệm vụ thủ công",
            "estimated_minutes": int(estimated_minutes),
            "scheduled_date": scheduled_date.isoformat(),
            "scheduled_start": scheduled_start.isoformat() if scheduled_start is not None else None,
            "scheduled_end": scheduled_end.isoformat() if scheduled_end is not None else None,
        }

        mode_upper = (avail_config.mode or "MODE_A").strip().upper()
        is_mode_b = mode_upper in ("MODE_B", "FIXED_SLOTS", "SLOTS")

        soft_warnings: list[SoftOverflowWarningDTO] = []
        if is_mode_b:
            violations, soft_warnings = SpatioTemporalRuleEngine.validate_mode_b_slots(
                tasks=[candidate_task],
                availability=avail_config,
                existing_tasks=effective_existing,
                current_roadmap_target_date=target_date,
            )
        else:
            violations = SpatioTemporalRuleEngine.validate_mode_a_quota(
                tasks=[candidate_task],
                availability=avail_config,
                existing_tasks=effective_existing,
                current_roadmap_target_date=target_date,
            )

        # Check fresh Google Calendar busy intervals for direct time collisions
        calendar_conflicts: list[dict[str, Any]] = []
        if scheduled_start is not None and scheduled_end is not None:
            user_tz = _resolve_tz(user_tz_name)
            s_cmp = (
                scheduled_start.astimezone(UTC)
                if scheduled_start.tzinfo is not None
                else scheduled_start.replace(tzinfo=user_tz).astimezone(UTC)
            )
            e_cmp = (
                scheduled_end.astimezone(UTC)
                if scheduled_end.tzinfo is not None
                else scheduled_end.replace(tzinfo=user_tz).astimezone(UTC)
            )
            for blocked in effective_avail.blocked_intervals:
                if blocked.get("source") != "GOOGLE_CALENDAR_BUSY":
                    continue
                b_start = parse_iso_datetime(blocked.get("start_time"))
                b_end = parse_iso_datetime(blocked.get("end_time"))
                if b_start is None or b_end is None:
                    continue
                b_s_utc = b_start.astimezone(UTC) if b_start.tzinfo else b_start.replace(tzinfo=UTC)
                b_e_utc = b_end.astimezone(UTC) if b_end.tzinfo else b_end.replace(tzinfo=UTC)
                if s_cmp < b_e_utc and b_s_utc < e_cmp:
                    calendar_conflicts.append(
                        {
                            "source": "GOOGLE_CALENDAR_BUSY",
                            "conflict_start": b_start.isoformat(),
                            "conflict_end": b_end.isoformat(),
                        }
                    )

        violation_dicts = [v.to_dict() for v in violations]
        soft_dicts = [w.to_dict() for w in soft_warnings]
        if soft_dicts and not confirm_soft_overflow:
            for w in soft_dicts:
                violation_dicts.append(
                    {
                        "task_index": w.get("task_index", 0),
                        "field": "scheduled_end",
                        "rule_code": "SOFT_OVERFLOW_CONFIRMATION_REQUIRED",
                        "expected_bound": "Trong khung giờ rảnh hoặc xác nhận Soft Overflow <= 30 phút",
                        "actual_value": f"Tràn {w.get('overflow_minutes', 0)} phút",
                        "suggested_fix": str(w.get("message", "")),
                    }
                )

        is_valid = len(violation_dicts) == 0 and len(calendar_conflicts) == 0
        return ManualSlotValidationResultDTO(
            is_valid=is_valid,
            violations=tuple(violation_dicts),
            soft_overflow_warnings=tuple(soft_dicts),
            calendar_conflicts=tuple(calendar_conflicts),
            official_schedule_id=official_schedule_id,
            availability_mode=avail_config.mode,
        )

    async def _is_external_calendar_active(self, user_id: UUID) -> bool:
        cal_port = create_calendar_connection_query_port(self._session)
        for provider in ("GOOGLE", "OUTLOOK", "LOCAL_MOCK"):
            snap = await cal_port.get_connection_snapshot(user_id=user_id, provider=provider)
            if snap is not None and snap.is_active:
                return True
        return False

    async def sync_task_lifecycle_to_blocks(
        self,
        *,
        task_id: UUID,
        roadmap_id: UUID,
        new_status: str,
        scheduled_date: date | None,
        scheduled_start: datetime | None,
        scheduled_end: datetime | None,
        estimated_minutes: int,
        now: datetime,
    ) -> None:
        rm_stmt = select(RoadmapORM.user_id).where(RoadmapORM.id == roadmap_id)
        owner_id = (await self._session.execute(rm_stmt)).scalar_one_or_none()
        calendar_active = (
            await self._is_external_calendar_active(owner_id) if owner_id is not None else False
        )

        block_stmt = (
            select(ScheduleBlockORM)
            .where(
                ScheduleBlockORM.roadmap_id == roadmap_id,
                ScheduleBlockORM.task_id == task_id,
            )
            .order_by(ScheduleBlockORM.sequence_in_task.asc(), ScheduleBlockORM.created_at.asc())
        )
        blocks = list((await self._session.execute(block_stmt)).scalars().all())
        upper_status = new_status.strip().upper()

        if upper_status == "CANCELLED" or scheduled_date is None:
            for block in blocks:
                if block.status != "CANCELLED":
                    block.status = "CANCELLED"
                    block.updated_at = now
                    if calendar_active:
                        block.sync_status = "PENDING_SYNC"
            await self._session.flush()
            return

        if upper_status == "COMPLETED":
            for block in blocks:
                if block.status != "CANCELLED":
                    block.status = "COMPLETED"
                    block.updated_at = now
            await self._session.flush()
            return

        # Reopened or rescheduled (TODO / IN_PROGRESS with scheduled_date)
        active_blocks = [b for b in blocks if b.status != "CANCELLED"]

        if scheduled_start is not None and scheduled_end is not None:
            if active_blocks:
                primary = active_blocks[0]
                primary.block_date = scheduled_date
                primary.start_time = scheduled_start
                primary.end_time = scheduled_end
                primary.scheduled_duration_minutes = max(10, min(240, int(estimated_minutes)))
                primary.status = "PLANNED"
                primary.updated_at = now
                if calendar_active:
                    primary.sync_status = "PENDING_SYNC"
                for extra in active_blocks[1:]:
                    extra.status = "CANCELLED"
                    extra.updated_at = now
                    if calendar_active:
                        extra.sync_status = "PENDING_SYNC"
            else:
                sched_stmt = select(OfficialScheduleORM.id).where(
                    OfficialScheduleORM.roadmap_id == roadmap_id
                )
                official_schedule_id = (
                    await self._session.execute(sched_stmt)
                ).scalar_one_or_none()
                if official_schedule_id is not None:
                    new_block = ScheduleBlockORM(
                        id=uuid7(),
                        roadmap_id=roadmap_id,
                        official_schedule_id=official_schedule_id,
                        task_id=task_id,
                        sequence_in_task=1,
                        block_type="STUDY",
                        block_date=scheduled_date,
                        start_time=scheduled_start,
                        end_time=scheduled_end,
                        scheduled_duration_minutes=max(10, min(240, int(estimated_minutes))),
                        is_protected=False,
                        status="PLANNED",
                        sync_status="PENDING_SYNC" if calendar_active else "SYNCED",
                        created_at=now,
                        updated_at=now,
                    )
                    self._session.add(new_block)
        else:
            # Reopen or Mode-A date-only reschedule without explicit start/end
            for block in active_blocks:
                if block.status == "COMPLETED":
                    block.status = "PLANNED"
                    block.updated_at = now
                if block.block_date != scheduled_date:
                    delta_days = (scheduled_date - block.block_date).days
                    block.block_date = scheduled_date
                    block.start_time = block.start_time + timedelta(days=delta_days)
                    block.end_time = block.end_time + timedelta(days=delta_days)
                    block.updated_at = now
                    if calendar_active:
                        block.sync_status = "PENDING_SYNC"
            if not active_blocks and blocks:
                # Reactivate previously cancelled block on Mode-A reschedule from backlog
                latest = blocks[0]
                delta_days = (scheduled_date - latest.block_date).days
                latest.block_date = scheduled_date
                latest.start_time = latest.start_time + timedelta(days=delta_days)
                latest.end_time = latest.end_time + timedelta(days=delta_days)
                latest.scheduled_duration_minutes = max(10, min(240, int(estimated_minutes)))
                latest.status = "PLANNED"
                latest.updated_at = now
                if calendar_active:
                    latest.sync_status = "PENDING_SYNC"

        await self._session.flush()

    async def deduct_overdue_reschedule_budget(
        self,
        roadmap_id: UUID,
        now: datetime,
    ) -> int:
        stmt = select(RoadmapORM).where(RoadmapORM.id == roadmap_id).with_for_update()
        roadmap = (await self._session.execute(stmt)).scalar_one_or_none()
        if roadmap is None:
            raise RoadmapNotFoundError(roadmap_id)

        user_tz_name = "Asia/Ho_Chi_Minh"
        user_snap = await create_user_query_port(self._session).get_user_by_id(roadmap.user_id)
        if user_snap is not None and user_snap.timezone:
            user_tz_name = user_snap.timezone
        user_tz = _resolve_tz(user_tz_name)
        ref_now = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
        local_today = ref_now.astimezone(user_tz).date()
        current_monday = local_today - timedelta(days=local_today.weekday())

        if roadmap.budget_week_start is None or roadmap.budget_week_start < current_monday:
            roadmap.weekly_reschedule_used = 0
            roadmap.budget_week_start = current_monday

        budget = int(roadmap.weekly_reschedule_budget)
        used = int(roadmap.weekly_reschedule_used)
        if used >= budget:
            raise RescheduleBudgetExhaustedError()

        roadmap.weekly_reschedule_used = used + 1
        roadmap.updated_at = ref_now
        await self._session.flush()
        return int(roadmap.weekly_reschedule_used)

    async def record_study_activity_and_check_completion(
        self,
        roadmap_id: UUID,
        activity_at: datetime,
        all_tasks_completed: bool,
        now: datetime,
    ) -> str:
        stmt = select(RoadmapORM).where(RoadmapORM.id == roadmap_id).with_for_update()
        roadmap = (await self._session.execute(stmt)).scalar_one_or_none()
        if roadmap is None:
            raise RoadmapNotFoundError(roadmap_id)

        if roadmap.last_study_activity_at is None or activity_at > roadmap.last_study_activity_at:
            roadmap.last_study_activity_at = activity_at

        if all_tasks_completed and roadmap.status == "ACTIVE":
            roadmap.status = "COMPLETED"

        roadmap.updated_at = now
        await self._session.flush()
        return roadmap.status


def _planning_execution_bridge_factory_impl(session: AsyncSession) -> PlanningExecutionBridgePort:
    return PlanningExecutionBridgeAdapter(session)


register_planning_execution_bridge_factory(_planning_execution_bridge_factory_impl)
