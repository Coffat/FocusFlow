from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.planning.domain.models.goal import Goal
from src.planning.domain.models.milestone import Milestone
from src.planning.domain.models.roadmap import Roadmap
from src.planning.domain.models.schedule import OfficialSchedule, ScheduleProposal


class GoalRepositoryPort(Protocol):
    async def save(self, goal: Goal) -> Goal: ...

    async def get_by_id(self, goal_id: UUID) -> Goal | None: ...

    async def get_by_id_for_user(self, goal_id: UUID, user_id: UUID) -> Goal | None: ...

    async def list_by_user_id(self, user_id: UUID) -> list[Goal]: ...


class RoadmapRepositoryPort(Protocol):
    async def save(self, roadmap: Roadmap) -> Roadmap: ...

    async def get_by_id(self, roadmap_id: UUID) -> Roadmap | None: ...

    async def get_by_id_for_user(self, roadmap_id: UUID, user_id: UUID) -> Roadmap | None: ...

    async def list_by_user_id(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
    ) -> list[Roadmap]: ...

    async def count_active_by_user_id(
        self,
        user_id: UUID,
        *,
        exclude_roadmap_id: UUID | None = None,
    ) -> int: ...


class MilestoneRepositoryPort(Protocol):
    async def save_many(
        self,
        roadmap_id: UUID,
        milestones: Sequence[Milestone],
    ) -> list[Milestone]: ...

    async def list_by_roadmap_id(self, roadmap_id: UUID) -> list[Milestone]: ...

    async def approve_all_for_roadmap(
        self,
        roadmap_id: UUID,
        now: datetime,
    ) -> list[Milestone]: ...


class ScheduleProposalRepositoryPort(Protocol):
    async def save(self, proposal: ScheduleProposal) -> ScheduleProposal: ...

    async def get_by_id(self, proposal_id: UUID) -> ScheduleProposal | None: ...

    async def get_current_draft(self, roadmap_id: UUID) -> ScheduleProposal | None: ...

    async def discard_existing_drafts(self, roadmap_id: UUID, now: datetime) -> int: ...


class OfficialScheduleRepositoryPort(Protocol):
    async def save(self, schedule: OfficialSchedule) -> OfficialSchedule: ...

    async def get_by_roadmap_id(self, roadmap_id: UUID) -> OfficialSchedule | None: ...
