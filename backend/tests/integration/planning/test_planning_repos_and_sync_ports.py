from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from sqlalchemy import delete, select
from uuid6 import uuid7

from src.account.infrastructure.orm import UserORM
from src.evaluation.infrastructure.adapters import ScheduleChangeLogAdapter
from src.evaluation.infrastructure.orm import ScheduleChangeLogORM
from src.execution.infrastructure.adapters import ExecutionScheduleSyncAdapter
from src.execution.infrastructure.orm import TaskDependencyORM, TaskORM
from src.execution.public_api import (
    ProposedDependencySyncItemDTO,
    ProposedTaskSyncItemDTO,
)
from src.planning.domain.models import (
    Goal,
    Milestone,
    MilestoneStatus,
    OfficialSchedule,
    Roadmap,
    RoadmapStatus,
    ScheduleProposal,
)
from src.planning.infrastructure.repositories import (
    SqlAlchemyGoalRepository,
    SqlAlchemyMilestoneRepository,
    SqlAlchemyOfficialScheduleRepository,
    SqlAlchemyRoadmapRepository,
    SqlAlchemyScheduleProposalRepository,
)
from src.shared_kernel.infrastructure.database.session import async_session_factory


@pytest.mark.asyncio
async def test_planning_repositories_and_execution_os03_merge_and_evaluation_change_log() -> None:
    """Integration test on PostgreSQL 16 verifying:
    1. Planning repositories (`Goal`, `Roadmap`, `Milestone`, `ScheduleProposal`, `OfficialSchedule`)
       persist and query cleanly with add/flush.
    2. `ExecutionScheduleSyncAdapter.sync_official_schedule_tasks` implements OS-03 Merge / Future Shift:
       preserves `COMPLETED` tasks from the past, replaces `TODO` tasks with newly applied tasks
       and dependencies, and queries active roadmap tasks for Cross-Roadmap EDF (`OS-04`).
    3. `ScheduleChangeLogAdapter.log_schedule_change` inserts an audit record in `schedule_change_logs`.
    """
    user_id: UUID = uuid7()
    now = datetime(2026, 10, 30, 9, 0, tzinfo=UTC)

    async with async_session_factory() as session:
        user = UserORM(
            id=user_id,
            email=f"phase2_plan_{user_id.hex[:8]}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="Phase 2 Planning Learner",
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE",
            is_locked=False,
        )
        session.add(user)
        await session.commit()

    try:
        async with async_session_factory() as session:
            goal_repo = SqlAlchemyGoalRepository(session)
            roadmap_repo = SqlAlchemyRoadmapRepository(session)
            milestone_repo = SqlAlchemyMilestoneRepository(session)
            proposal_repo = SqlAlchemyScheduleProposalRepository(session)
            schedule_repo = SqlAlchemyOfficialScheduleRepository(session)
            exec_sync = ExecutionScheduleSyncAdapter(session)
            change_log = ScheduleChangeLogAdapter(session)

            # 1. Create Goal & Roadmap & Milestones
            goal = Goal(
                user_id=user_id,
                title="Chinh phục Hệ thống Phân tán",
                raw_description="Nắm vững Raft, Paxos và Event-Driven Architecture",
                target_date=date(2026, 12, 20),
                created_at=now,
                updated_at=now,
            )
            await goal_repo.save(goal)

            roadmap = Roadmap(
                user_id=user_id,
                goal_id=goal.id,
                title="Lộ trình Hệ thống Phân tán",
                description="Lộ trình 8 tuần",
                status=RoadmapStatus.INITIALIZED,
                start_date=date(2026, 11, 1),
                target_date=date(2026, 12, 20),
                created_at=now,
                updated_at=now,
            )
            await roadmap_repo.save(roadmap)

            m1 = Milestone(
                roadmap_id=roadmap.id,
                sequence_order=1,
                title="Chặng 1: Giao thức đồng thuận",
                status=MilestoneStatus.PENDING,
                created_at=now,
                updated_at=now,
            )
            m2 = Milestone(
                roadmap_id=roadmap.id,
                sequence_order=2,
                title="Chặng 2: Transactional Outbox & Saga",
                status=MilestoneStatus.PENDING,
                created_at=now,
                updated_at=now,
            )
            await milestone_repo.save_many(roadmap.id, [m1, m2])
            approved_milestones = await milestone_repo.approve_all_for_roadmap(roadmap.id, now)
            assert all(m.status == MilestoneStatus.APPROVED for m in approved_milestones)

            # 2. Save Draft Proposal & OfficialSchedule
            proposal = ScheduleProposal(
                roadmap_id=roadmap.id,
                user_id=user_id,
                proposal_data={"tasks": [{"title": "Task ban đầu"}]},
                created_at=now,
                updated_at=now,
            )
            await proposal_repo.save(proposal)
            current_draft = await proposal_repo.get_current_draft(roadmap.id)
            assert current_draft is not None
            assert current_draft.id == proposal.id

            official_schedule = OfficialSchedule(
                roadmap_id=roadmap.id,
                total_sessions=2,
                total_planned_minutes=120,
                activated_at=now,
                created_at=now,
                updated_at=now,
            )
            await schedule_repo.save(official_schedule)

            # 3. Seed 1 COMPLETED task and 1 TODO task in `tasks`
            completed_task_id = uuid7()
            pending_task_id = uuid7()
            session.add_all(
                [
                    TaskORM(
                        id=completed_task_id,
                        roadmap_id=roadmap.id,
                        milestone_id=m1.id,
                        official_schedule_id=official_schedule.id,
                        title="Đã hoàn thành: Đọc bài báo Raft",
                        estimated_minutes=60,
                        scheduled_date=date(2026, 11, 1),
                        status="COMPLETED",
                        completed_at=now,
                        reschedule_count=0,
                        created_at=now,
                        updated_at=now,
                    ),
                    TaskORM(
                        id=pending_task_id,
                        roadmap_id=roadmap.id,
                        milestone_id=m1.id,
                        official_schedule_id=official_schedule.id,
                        title="Chưa làm: Sẽ bị thay thế khi Merge OS-03",
                        estimated_minutes=60,
                        scheduled_date=date(2026, 11, 2),
                        status="TODO",
                        completed_at=None,
                        reschedule_count=0,
                        created_at=now,
                        updated_at=now,
                    ),
                ]
            )
            await session.flush()

            # 4. Run OS-03 Merge / Future Shift via ExecutionScheduleSyncAdapter
            new_task_1_id = uuid7()
            new_task_2_id = uuid7()
            sync_res = await exec_sync.sync_official_schedule_tasks(
                roadmap_id=roadmap.id,
                official_schedule_id=official_schedule.id,
                proposed_tasks=[
                    ProposedTaskSyncItemDTO(
                        task_id=new_task_1_id,
                        milestone_id=m1.id,
                        title="Cài đặt bầu cử Leader trong Raft",
                        estimated_minutes=60,
                        scheduled_date=date(2026, 11, 3),
                    ),
                    ProposedTaskSyncItemDTO(
                        task_id=new_task_2_id,
                        milestone_id=m2.id,
                        title="Cài đặt Outbox Relay",
                        estimated_minutes=90,
                        scheduled_date=date(2026, 11, 4),
                    ),
                ],
                proposed_dependencies=[
                    ProposedDependencySyncItemDTO(
                        predecessor_id=completed_task_id,
                        successor_id=new_task_1_id,
                        is_mandatory=True,
                    ),
                    ProposedDependencySyncItemDTO(
                        predecessor_id=new_task_1_id,
                        successor_id=new_task_2_id,
                        is_mandatory=True,
                    ),
                ],
                now=now,
            )

            assert sync_res.preserved_completed_tasks_count == 1
            assert sync_res.replaced_tasks_count == 1
            assert sync_res.inserted_tasks_count == 2
            assert sync_res.total_active_sessions == 3
            assert sync_res.total_planned_minutes == 210

            # Verify DB state of `tasks` and `task_dependencies`
            db_tasks = list(
                (await session.execute(select(TaskORM).where(TaskORM.roadmap_id == roadmap.id)))
                .scalars()
                .all()
            )
            db_task_ids = {t.id for t in db_tasks}
            assert completed_task_id in db_task_ids
            assert pending_task_id not in db_task_ids
            assert new_task_1_id in db_task_ids
            assert new_task_2_id in db_task_ids

            db_deps = list(
                (
                    await session.execute(
                        select(TaskDependencyORM).where(TaskDependencyORM.roadmap_id == roadmap.id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(db_deps) == 2

            # Verify get_active_roadmaps_tasks (without cross-context JOIN)
            queried_tasks = await exec_sync.get_active_roadmaps_tasks(
                user_id=user_id,
                active_roadmap_ids=[roadmap.id],
                roadmap_target_dates={roadmap.id: roadmap.target_date},
            )
            assert len(queried_tasks) == 3
            assert all(qt.roadmap_target_date == date(2026, 12, 20) for qt in queried_tasks)

            # 5. Record ScheduleChangeLog via ScheduleChangeLogAdapter
            log_entry = await change_log.log_schedule_change(
                roadmap_id=roadmap.id,
                schedule_id=official_schedule.id,
                trigger_type="INITIAL_APPLY",
                reason="Apply ScheduleProposal into OfficialSchedule (OS-03 Merge)",
                affected_tasks_count=sync_res.affected_tasks_count,
                total_shifted_minutes=sync_res.total_shifted_minutes,
                diff_payload={
                    "preserved_completed": sync_res.preserved_completed_tasks_count,
                    "inserted": sync_res.inserted_tasks_count,
                },
                now=now,
            )
            assert log_entry.trigger_type == "AI_REPLAN"
            assert log_entry.affected_tasks_count == 3
            assert log_entry.diff_payload["original_trigger_type"] == "INITIAL_APPLY"

            await session.commit()

            persisted_log = (
                await session.execute(
                    select(ScheduleChangeLogORM).where(ScheduleChangeLogORM.id == log_entry.id)
                )
            ).scalar_one()
            assert persisted_log.roadmap_id == roadmap.id
            assert persisted_log.schedule_id == official_schedule.id
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()
