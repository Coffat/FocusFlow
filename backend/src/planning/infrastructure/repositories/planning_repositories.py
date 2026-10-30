from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    MilestoneRepositoryPort,
    OfficialScheduleRepositoryPort,
    RoadmapRepositoryPort,
    ScheduleProposalRepositoryPort,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import (
    OfficialSchedule,
    ScheduleProposal,
    ScheduleProposalStatus,
)
from src.planning.infrastructure.orm.planning_orm import (
    GoalORM,
    MilestoneORM,
    OfficialScheduleORM,
    RoadmapORM,
    ScheduleProposalORM,
)


def _ensure_utc(dt: datetime) -> datetime:
    if dt == datetime.min:
        return datetime.now(UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class SqlAlchemyGoalRepository(GoalRepositoryPort):
    """Repository for `Goal` aggregate (add/flush only, never commit)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: GoalORM) -> Goal:
        return Goal(
            id=row.id,
            user_id=row.user_id,
            title=row.title,
            raw_description=row.raw_description,
            target_date=row.target_date,
            status=GoalStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def save(self, goal: Goal) -> Goal:
        row = await self._session.get(GoalORM, goal.id)
        now = _ensure_utc(goal.updated_at)
        created = _ensure_utc(goal.created_at)
        raw_desc = goal.raw_description if goal.raw_description is not None else goal.title

        if row is None:
            row = GoalORM(
                id=goal.id,
                user_id=goal.user_id,
                title=goal.title,
                raw_description=raw_desc,
                target_date=goal.target_date,
                status=goal.status.value,
                created_at=created,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.title = goal.title
            row.raw_description = raw_desc
            row.target_date = goal.target_date
            row.status = goal.status.value
            row.updated_at = now

        await self._session.flush()
        return self._to_domain(row)

    async def get_by_id(self, goal_id: UUID) -> Goal | None:
        row = await self._session.get(GoalORM, goal_id)
        if row is None:
            return None
        return self._to_domain(row)

    async def list_by_user_id(self, user_id: UUID) -> list[Goal]:
        stmt = select(GoalORM).where(GoalORM.user_id == user_id).order_by(GoalORM.created_at.desc())
        rows = list((await self._session.execute(stmt)).scalars().all())
        return [self._to_domain(r) for r in rows]


class SqlAlchemyRoadmapRepository(RoadmapRepositoryPort):
    """Repository for `Roadmap` aggregate (add/flush only, never commit)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: RoadmapORM) -> Roadmap:
        return Roadmap(
            id=row.id,
            user_id=row.user_id,
            goal_id=row.goal_id,
            title=row.title,
            description=row.description,
            status=RoadmapStatus(row.status),
            start_date=row.start_date,
            target_date=row.target_date,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def save(self, roadmap: Roadmap) -> Roadmap:
        row = await self._session.get(RoadmapORM, roadmap.id)
        now = _ensure_utc(roadmap.updated_at)
        created = _ensure_utc(roadmap.created_at)

        if row is None:
            row = RoadmapORM(
                id=roadmap.id,
                user_id=roadmap.user_id,
                goal_id=roadmap.goal_id,
                title=roadmap.title,
                description=roadmap.description,
                status=roadmap.status.value,
                start_date=roadmap.start_date,
                target_date=roadmap.target_date,
                created_at=created,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.title = roadmap.title
            row.description = roadmap.description
            row.status = roadmap.status.value
            row.start_date = roadmap.start_date
            row.target_date = roadmap.target_date
            row.updated_at = now

        await self._session.flush()
        return self._to_domain(row)

    async def get_by_id(self, roadmap_id: UUID) -> Roadmap | None:
        row = await self._session.get(RoadmapORM, roadmap_id)
        if row is None:
            return None
        return self._to_domain(row)

    async def get_by_id_for_user(self, roadmap_id: UUID, user_id: UUID) -> Roadmap | None:
        stmt = select(RoadmapORM).where(
            RoadmapORM.id == roadmap_id,
            RoadmapORM.user_id == user_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def list_by_user_id(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
    ) -> list[Roadmap]:
        stmt = select(RoadmapORM).where(RoadmapORM.user_id == user_id)
        if status is not None:
            stmt = stmt.where(RoadmapORM.status == status.strip().upper())
        stmt = stmt.order_by(
            RoadmapORM.target_date.asc().nulls_last(),
            RoadmapORM.created_at.desc(),
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        return [self._to_domain(r) for r in rows]

    async def count_active_by_user_id(
        self,
        user_id: UUID,
        *,
        exclude_roadmap_id: UUID | None = None,
    ) -> int:
        stmt = select(func.count(RoadmapORM.id)).where(
            RoadmapORM.user_id == user_id,
            RoadmapORM.status == RoadmapStatus.ACTIVE.value,
        )
        if exclude_roadmap_id is not None:
            stmt = stmt.where(RoadmapORM.id != exclude_roadmap_id)
        count = (await self._session.execute(stmt)).scalar_one()
        return int(count or 0)


class SqlAlchemyMilestoneRepository(MilestoneRepositoryPort):
    """Repository for `Milestone` entities (add/flush only, never commit)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: MilestoneORM) -> Milestone:
        return Milestone(
            id=row.id,
            roadmap_id=row.roadmap_id,
            sequence_order=row.sequence_order,
            title=row.title,
            description=row.description,
            status=MilestoneStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def save_many(
        self,
        roadmap_id: UUID,
        milestones: Sequence[Milestone],
    ) -> list[Milestone]:
        keep_ids = {m.id for m in milestones}
        existing_stmt = select(MilestoneORM).where(MilestoneORM.roadmap_id == roadmap_id)
        existing_rows = list((await self._session.execute(existing_stmt)).scalars().all())
        existing_map: dict[UUID, MilestoneORM] = {r.id: r for r in existing_rows}

        remove_ids = [r.id for r in existing_rows if r.id not in keep_ids]
        if remove_ids:
            await self._session.execute(delete(MilestoneORM).where(MilestoneORM.id.in_(remove_ids)))
            await self._session.flush()

        saved_rows: list[MilestoneORM] = []
        for idx, m in enumerate(milestones, start=1):
            seq = m.sequence_order if m.sequence_order >= 1 else idx
            now = _ensure_utc(m.updated_at)
            created = _ensure_utc(m.created_at)
            if m.id in existing_map:
                row = existing_map[m.id]
                row.sequence_order = seq
                row.title = m.title
                row.description = m.description
                row.status = m.status.value
                row.updated_at = now
            else:
                row = MilestoneORM(
                    id=m.id,
                    roadmap_id=roadmap_id,
                    sequence_order=seq,
                    title=m.title,
                    description=m.description,
                    status=m.status.value,
                    created_at=created,
                    updated_at=now,
                )
                self._session.add(row)
            saved_rows.append(row)

        await self._session.flush()
        saved_rows.sort(key=lambda r: r.sequence_order)
        return [self._to_domain(r) for r in saved_rows]

    async def list_by_roadmap_id(self, roadmap_id: UUID) -> list[Milestone]:
        stmt = (
            select(MilestoneORM)
            .where(MilestoneORM.roadmap_id == roadmap_id)
            .order_by(MilestoneORM.sequence_order.asc())
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        return [self._to_domain(r) for r in rows]

    async def approve_all_for_roadmap(
        self,
        roadmap_id: UUID,
        now: datetime,
    ) -> list[Milestone]:
        effective_now = _ensure_utc(now)
        stmt = (
            select(MilestoneORM)
            .where(MilestoneORM.roadmap_id == roadmap_id)
            .order_by(MilestoneORM.sequence_order.asc())
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        for row in rows:
            if row.status == MilestoneStatus.PENDING.value:
                row.status = MilestoneStatus.APPROVED.value
                row.updated_at = effective_now
        await self._session.flush()
        return [self._to_domain(r) for r in rows]


class SqlAlchemyScheduleProposalRepository(ScheduleProposalRepositoryPort):
    """Repository for `ScheduleProposal` aggregate (add/flush only, never commit)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: ScheduleProposalORM) -> ScheduleProposal:
        return ScheduleProposal(
            id=row.id,
            roadmap_id=row.roadmap_id,
            user_id=row.user_id,
            proposal_data=dict(row.proposal_data or {}),
            status=ScheduleProposalStatus(row.status),
            applied_at=row.applied_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def discard_existing_drafts(self, roadmap_id: UUID, now: datetime) -> int:
        effective_now = _ensure_utc(now)
        stmt = (
            update(ScheduleProposalORM)
            .where(
                ScheduleProposalORM.roadmap_id == roadmap_id,
                ScheduleProposalORM.status == ScheduleProposalStatus.DRAFT.value,
            )
            .values(
                status=ScheduleProposalStatus.DISCARDED.value,
                updated_at=effective_now,
            )
        )
        res = await self._session.execute(stmt)
        await self._session.flush()
        return int(res.rowcount or 0)  # type: ignore[attr-defined]

    async def save(self, proposal: ScheduleProposal) -> ScheduleProposal:
        row = await self._session.get(ScheduleProposalORM, proposal.id)
        now = _ensure_utc(proposal.updated_at)
        created = _ensure_utc(proposal.created_at)

        if row is None:
            row = ScheduleProposalORM(
                id=proposal.id,
                roadmap_id=proposal.roadmap_id,
                user_id=proposal.user_id,
                proposal_data=dict(proposal.proposal_data),
                status=proposal.status.value,
                applied_at=proposal.applied_at,
                created_at=created,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.proposal_data = dict(proposal.proposal_data)
            row.status = proposal.status.value
            row.applied_at = proposal.applied_at
            row.updated_at = now

        await self._session.flush()
        return self._to_domain(row)

    async def get_by_id(self, proposal_id: UUID) -> ScheduleProposal | None:
        row = await self._session.get(ScheduleProposalORM, proposal_id)
        if row is None:
            return None
        return self._to_domain(row)

    async def get_current_draft(self, roadmap_id: UUID) -> ScheduleProposal | None:
        stmt = select(ScheduleProposalORM).where(
            ScheduleProposalORM.roadmap_id == roadmap_id,
            ScheduleProposalORM.status == ScheduleProposalStatus.DRAFT.value,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)


class SqlAlchemyOfficialScheduleRepository(OfficialScheduleRepositoryPort):
    """Repository for `OfficialSchedule` aggregate (add/flush only, never commit)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: OfficialScheduleORM) -> OfficialSchedule:
        return OfficialSchedule(
            id=row.id,
            roadmap_id=row.roadmap_id,
            total_sessions=row.total_sessions,
            total_planned_minutes=row.total_planned_minutes,
            activated_at=row.activated_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def save(self, schedule: OfficialSchedule) -> OfficialSchedule:
        row = await self._session.get(OfficialScheduleORM, schedule.id)
        if row is None:
            by_roadmap_stmt = select(OfficialScheduleORM).where(
                OfficialScheduleORM.roadmap_id == schedule.roadmap_id
            )
            row = (await self._session.execute(by_roadmap_stmt)).scalar_one_or_none()

        activated = _ensure_utc(schedule.activated_at)
        created = _ensure_utc(schedule.created_at)
        updated = _ensure_utc(schedule.updated_at)

        if row is None:
            row = OfficialScheduleORM(
                id=schedule.id,
                roadmap_id=schedule.roadmap_id,
                total_sessions=schedule.total_sessions,
                total_planned_minutes=schedule.total_planned_minutes,
                activated_at=activated,
                created_at=created,
                updated_at=updated,
            )
            self._session.add(row)
        else:
            row.total_sessions = schedule.total_sessions
            row.total_planned_minutes = schedule.total_planned_minutes
            row.activated_at = activated
            row.updated_at = updated

        await self._session.flush()
        return self._to_domain(row)

    async def get_by_roadmap_id(self, roadmap_id: UUID) -> OfficialSchedule | None:
        stmt = select(OfficialScheduleORM).where(OfficialScheduleORM.roadmap_id == roadmap_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)


GoalRepository = SqlAlchemyGoalRepository
RoadmapRepository = SqlAlchemyRoadmapRepository
MilestoneRepository = SqlAlchemyMilestoneRepository
ScheduleProposalRepository = SqlAlchemyScheduleProposalRepository
OfficialScheduleRepository = SqlAlchemyOfficialScheduleRepository
