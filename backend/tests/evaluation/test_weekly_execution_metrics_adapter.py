"""DB integration tests for WeeklyExecutionMetricsAdapter (task_type_breakdown & WoW metrics)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from sqlalchemy import delete
from uuid6 import uuid7

from src.account.infrastructure.orm import UserORM
from src.execution.infrastructure.adapters.weekly_execution_metrics_adapter import (
    WeeklyExecutionMetricsAdapter,
)
from src.execution.infrastructure.orm.session_orm import StudySessionORM
from src.execution.infrastructure.orm.task_orm import TaskORM
from src.planning.infrastructure.orm.planning_orm import (
    GoalORM,
    MilestoneORM,
    RoadmapORM,
    ScheduleProposalORM,
)
from src.shared_kernel.infrastructure.database.session import async_session_factory


@pytest.mark.asyncio
async def test_weekly_execution_metrics_adapter_computes_task_type_breakdown_and_wow() -> None:
    """Verify real SQL aggregation for task_type_breakdown, previous_week_completed_minutes, and delta."""
    user_id: UUID = uuid7()
    period_start = date(2026, 11, 9)
    period_end = date(2026, 11, 15)

    async with async_session_factory() as session:
        session.add(
            UserORM(
                id=user_id,
                email=f"weekly_metrics_{user_id.hex[:8]}@focusflow.vn",
                password_hash="argon2id$mockhash",
                full_name="Weekly Metrics Learner",
                timezone="Asia/Ho_Chi_Minh",
                role="LEARNER",
                tier="FREE",
                is_locked=False,
            )
        )
        goal = GoalORM(
            user_id=user_id,
            title="Python Backend",
            raw_description="FastAPI + SQLAlchemy",
            target_date=date(2026, 12, 31),
            status="ACTIVE",
        )
        session.add(goal)
        await session.flush()

        roadmap = RoadmapORM(
            user_id=user_id,
            goal_id=goal.id,
            title="Python Roadmap",
            status="ACTIVE",
            start_date=date(2026, 11, 1),
            target_date=date(2026, 12, 31),
        )
        session.add(roadmap)
        await session.flush()

        milestone = MilestoneORM(
            roadmap_id=roadmap.id,
            sequence_order=1,
            title="M1",
            status="IN_PROGRESS",
        )
        session.add(milestone)
        await session.flush()

        t1_id = uuid7()
        t2_id = uuid7()
        t3_id = uuid7()
        t4_id = uuid7()

        session.add(
            ScheduleProposalORM(
                roadmap_id=roadmap.id,
                user_id=user_id,
                status="APPLIED",
                applied_at=datetime(2026, 11, 2, 8, 0, tzinfo=UTC),
                proposal_data={
                    "tasks": [
                        {"task_id": str(t1_id), "title": "Read Asyncio", "task_type": "THEORY"},
                        {"task_id": str(t2_id), "title": "Build API", "task_type": "PRACTICE"},
                        {"task_id": str(t3_id), "title": "Quiz Review", "task_type": "REVIEW"},
                        {"task_id": str(t4_id), "title": "Capstone", "task_type": "PROJECT"},
                    ]
                },
            )
        )

        session.add_all(
            [
                TaskORM(
                    id=t1_id,
                    roadmap_id=roadmap.id,
                    milestone_id=milestone.id,
                    title="Read Asyncio",
                    estimated_minutes=45,
                    status="COMPLETED",
                    scheduled_date=date(2026, 11, 10),
                    completed_at=datetime(2026, 11, 10, 10, 0, tzinfo=UTC),
                ),
                TaskORM(
                    id=t2_id,
                    roadmap_id=roadmap.id,
                    milestone_id=milestone.id,
                    title="Build API",
                    estimated_minutes=90,
                    status="COMPLETED",
                    scheduled_date=date(2026, 11, 11),
                    completed_at=datetime(2026, 11, 11, 10, 0, tzinfo=UTC),
                ),
                TaskORM(
                    id=t3_id,
                    roadmap_id=roadmap.id,
                    milestone_id=milestone.id,
                    title="Quiz Review",
                    estimated_minutes=30,
                    status="COMPLETED",
                    scheduled_date=date(2026, 11, 12),
                    completed_at=datetime(2026, 11, 12, 10, 0, tzinfo=UTC),
                ),
                TaskORM(
                    id=t4_id,
                    roadmap_id=roadmap.id,
                    milestone_id=milestone.id,
                    title="Capstone",
                    estimated_minutes=120,
                    status="TODO",
                    scheduled_date=date(2026, 11, 14),
                    completed_at=None,
                ),
            ]
        )

        # Previous 7 days (2026-11-02 .. 2026-11-08): 120 completed minutes
        session.add(
            StudySessionORM(
                user_id=user_id,
                roadmap_id=roadmap.id,
                started_at=datetime(2026, 11, 5, 9, 0, tzinfo=UTC),
                ended_at=datetime(2026, 11, 5, 11, 0, tzinfo=UTC),
                planned_minutes=120,
                actual_minutes=120,
                status="COMPLETED",
                last_heartbeat_at=datetime(2026, 11, 5, 11, 0, tzinfo=UTC),
            )
        )
        # Current period (2026-11-09 .. 2026-11-15): 150 completed minutes -> +25.0% WoW
        session.add(
            StudySessionORM(
                user_id=user_id,
                roadmap_id=roadmap.id,
                started_at=datetime(2026, 11, 11, 9, 0, tzinfo=UTC),
                ended_at=datetime(2026, 11, 11, 11, 30, tzinfo=UTC),
                planned_minutes=150,
                actual_minutes=150,
                status="COMPLETED",
                last_heartbeat_at=datetime(2026, 11, 11, 11, 30, tzinfo=UTC),
            )
        )
        await session.commit()

    try:
        async with async_session_factory() as session:
            adapter = WeeklyExecutionMetricsAdapter(session)
            dto = await adapter.get_roadmap_period_metrics(
                user_id=user_id,
                roadmap_id=roadmap.id,
                period_start=period_start,
                period_end=period_end,
            )

            assert dto.completed_minutes == 150
            assert dto.previous_week_completed_minutes == 120
            assert dto.week_over_week_delta_pct == 25.0
            assert dto.completed_tasks_count == 3
            assert dto.planned_tasks_count == 4
            assert dto.overdue_tasks_count == 1
            assert dto.task_type_breakdown == {
                "THEORY": {"completed_tasks_count": 1, "completed_minutes": 45},
                "PRACTICE": {"completed_tasks_count": 1, "completed_minutes": 90},
                "REVIEW": {"completed_tasks_count": 1, "completed_minutes": 30},
                "PROJECT": {"completed_tasks_count": 0, "completed_minutes": 0},
            }
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()
