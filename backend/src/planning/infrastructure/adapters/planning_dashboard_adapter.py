from datetime import date
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.planning.infrastructure.orm.planning_orm import (
    OfficialScheduleORM,
    RoadmapORM,
    ScheduleBlockORM,
    ScheduleProposalORM,
)
from src.planning.public_api import (
    PlanningActiveRoadmapDTO,
    PlanningDashboardQueryPort,
    PlanningDashboardScheduleBlockDTO,
    register_planning_dashboard_factory,
)

_DAY_LABELS: dict[int, str] = {
    1: "Thứ Hai",
    2: "Thứ Ba",
    3: "Thứ Tư",
    4: "Thứ Năm",
    5: "Thứ Sáu",
    6: "Thứ Bảy",
    7: "Chủ Nhật",
}


class PlanningDashboardAdapter(PlanningDashboardQueryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_roadmaps_for_user(self, user_id: UUID) -> list[PlanningActiveRoadmapDTO]:
        stmt = (
            select(RoadmapORM)
            .where(
                RoadmapORM.user_id == user_id,
                RoadmapORM.status == "ACTIVE",
            )
            .order_by(RoadmapORM.created_at.asc())
        )
        result = await self._session.execute(stmt)
        roadmaps = list(result.scalars().all())

        dtos: list[PlanningActiveRoadmapDTO] = []
        for r in roadmaps:
            roadmap_code = f"RD-{str(r.id)[:8].upper()}"
            commitment_hours = await self._calculate_commitment_hours(r)

            # Query task statistics for this roadmap
            tasks_stmt = text(
                """
                SELECT id, title, status, scheduled_date
                FROM tasks
                WHERE roadmap_id = :r_id
                ORDER BY scheduled_date ASC NULLS LAST, created_at ASC
                """
            )
            tasks_res = await self._session.execute(tasks_stmt, {"r_id": r.id})
            rows = tasks_res.fetchall()

            total_tasks = len(rows)
            completed_tasks = sum(1 for row in rows if row.status == "COMPLETED")
            progress_pct = (
                round((completed_tasks / total_tasks) * 100.0, 1) if total_tasks > 0 else 0.0
            )

            next_task_code: str | None = None
            next_task_title: str | None = None
            for row in rows:
                if row.status != "COMPLETED":
                    next_task_code = f"TSK-{str(row.id)[:8].upper()}"
                    next_task_title = row.title
                    break

            deadline_str = r.target_date.isoformat() if r.target_date else None

            dtos.append(
                PlanningActiveRoadmapDTO(
                    id=r.id,
                    code=roadmap_code,
                    title=r.title,
                    commitment_hours_per_week=commitment_hours,
                    deadline=deadline_str,
                    completed_tasks=completed_tasks,
                    total_tasks=total_tasks,
                    progress_pct=progress_pct,
                    next_task_code=next_task_code,
                    next_task_title=next_task_title,
                )
            )

        return dtos

    async def _calculate_commitment_hours(self, roadmap: RoadmapORM) -> float:
        # Check proposal data first
        prop_stmt = (
            select(ScheduleProposalORM.proposal_data)
            .where(
                ScheduleProposalORM.roadmap_id == roadmap.id,
            )
            .order_by(ScheduleProposalORM.created_at.desc())
            .limit(1)
        )
        prop_res = await self._session.execute(prop_stmt)
        prop_data = prop_res.scalar_one_or_none()
        if isinstance(prop_data, dict):
            if "weekly_commitment_hours" in prop_data:
                try:
                    return float(prop_data["weekly_commitment_hours"])
                except (ValueError, TypeError):
                    pass
            if "commitment_hours_per_week" in prop_data:
                try:
                    return float(prop_data["commitment_hours_per_week"])
                except (ValueError, TypeError):
                    pass

        # Check official schedule
        off_stmt = select(OfficialScheduleORM).where(OfficialScheduleORM.roadmap_id == roadmap.id)
        off_res = await self._session.execute(off_stmt)
        off = off_res.scalar_one_or_none()
        if off is not None and off.total_planned_minutes > 0:
            weeks = 4
            if roadmap.start_date and roadmap.target_date:
                diff_days = (roadmap.target_date - roadmap.start_date).days
                if diff_days >= 7:
                    weeks = max(1, diff_days // 7)
            return round((off.total_planned_minutes / 60.0) / weeks, 1)

        return 10.0

    async def get_week_schedule_blocks(
        self, user_id: UUID, start_date: date, end_date: date
    ) -> list[PlanningDashboardScheduleBlockDTO]:
        stmt = (
            select(ScheduleBlockORM, RoadmapORM.title)
            .join(RoadmapORM, RoadmapORM.id == ScheduleBlockORM.roadmap_id)
            .where(
                RoadmapORM.user_id == user_id,
                ScheduleBlockORM.block_date >= start_date,
                ScheduleBlockORM.block_date <= end_date,
            )
            .order_by(
                ScheduleBlockORM.block_date.asc(),
                ScheduleBlockORM.start_time.asc(),
            )
        )
        res = await self._session.execute(stmt)
        blocks = res.all()

        dtos: list[PlanningDashboardScheduleBlockDTO] = []
        for block, roadmap_title in blocks:
            dow = block.block_date.isoweekday()
            day_label = _DAY_LABELS.get(dow, f"Thứ {dow}")
            start_str = block.start_time.strftime("%H:%M")
            end_str = block.end_time.strftime("%H:%M")
            roadmap_code = f"RD-{str(block.roadmap_id)[:8].upper()}"

            category = "Study"
            low_title = roadmap_title.lower()
            if "ielts" in low_title or "english" in low_title or "tiếng anh" in low_title:
                category = "Language"
            elif (
                "go" in low_title
                or "backend" in low_title
                or "arch" in low_title
                or "system" in low_title
            ):
                category = "Engineering"
            elif "exam" in low_title or "mock" in low_title or "test" in low_title:
                category = "Assessment"

            title = block.block_type.capitalize()
            if block.task_id is not None:
                task_title_stmt = text("SELECT title FROM tasks WHERE id = :t_id")
                t_res = await self._session.execute(task_title_stmt, {"t_id": block.task_id})
                t_title = t_res.scalar_one_or_none()
                if t_title:
                    title = t_title

            pomodoro_count = max(1, block.scheduled_duration_minutes // 25)

            dtos.append(
                PlanningDashboardScheduleBlockDTO(
                    id=block.id,
                    day_of_week=dow,
                    day_label=day_label,
                    start_time=start_str,
                    end_time=end_str,
                    title=title,
                    category=category,
                    status=block.status,
                    pomodoro_count=pomodoro_count,
                    duration_minutes=block.scheduled_duration_minutes,
                    roadmap_code=roadmap_code,
                    description=block.placement_rationale,
                )
            )

        return dtos

    async def get_monthly_target_hours(self, user_id: UUID) -> float:
        active_roadmaps = await self.get_active_roadmaps_for_user(user_id)
        if not active_roadmaps:
            return 0.0
        return round(sum(r.commitment_hours_per_week * 4.0 for r in active_roadmaps), 1)


def _planning_dashboard_factory_impl(session: AsyncSession) -> PlanningDashboardQueryPort:
    return PlanningDashboardAdapter(session)


register_planning_dashboard_factory(_planning_dashboard_factory_impl)
