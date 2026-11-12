from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import delete
from uuid6 import uuid7

from src.account.infrastructure.orm import UserORM
from src.evaluation.application.use_cases.dashboard_summary import (
    GetDashboardSummaryUseCase,
)
from src.evaluation.infrastructure.repositories.intelligence_repository import (
    SqlAlchemyEvaluationIntelligenceRepository,
)
from src.execution.infrastructure.adapters.execution_dashboard_adapter import (
    ExecutionDashboardAdapter,
)
from src.execution.infrastructure.orm.session_orm import StudySessionORM
from src.execution.infrastructure.orm.task_orm import TaskORM
from src.planning.infrastructure.adapters.planning_dashboard_adapter import (
    PlanningDashboardAdapter,
)
from src.planning.infrastructure.orm.planning_orm import (
    GoalORM,
    MilestoneORM,
    OfficialScheduleORM,
    RoadmapORM,
    ScheduleBlockORM,
)
from src.shared_kernel.infrastructure.database.session import async_session_factory


@pytest.mark.asyncio
async def test_dashboard_summary_new_user_empty_state() -> None:
    """Test Case 1: Người dùng mới hoàn toàn (Empty State).

    Trả về DTO 0 giờ, 0 streak, mảng rỗng, insight nhắc nhở hoàn thành buổi học đầu tiên.
    """
    user_id: UUID = uuid7()

    async with async_session_factory() as session:
        user = UserORM(
            id=user_id,
            email=f"empty_learner_{user_id.hex[:8]}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="New Learner",
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE",
            is_locked=False,
        )
        session.add(user)
        await session.commit()

    try:
        async with async_session_factory() as session:
            planning_port = PlanningDashboardAdapter(session)
            execution_port = ExecutionDashboardAdapter(session)
            intel_repo = SqlAlchemyEvaluationIntelligenceRepository(session)

            use_case = GetDashboardSummaryUseCase(
                planning_port=planning_port,
                execution_port=execution_port,
                intelligence_repo=intel_repo,
            )

            summary = await use_case.execute(user_id)

            # KPIs check for empty state
            assert summary.kpi.monthly_hours == 0.0
            assert summary.kpi.target_hours == 0.0
            assert summary.kpi.monthly_progress_pct == 0.0
            assert summary.kpi.streak_days == 0
            assert summary.kpi.personal_best_streak == 0
            assert summary.kpi.completed_pomodoro_count == 0
            assert summary.kpi.deep_work_hours == 0.0
            assert summary.kpi.streak_history_last_7_days == [False] * 7

            # Distribution check
            assert len(summary.study_distribution) == 7
            assert all(d.hours == 0.0 for d in summary.study_distribution)
            assert any(d.is_today for d in summary.study_distribution)

            # Empty lists
            assert summary.active_roadmaps == []
            assert summary.today_queue == []
            assert summary.schedule_blocks == []

            # Adaptation status
            assert summary.adaptation_status.is_balanced is True
            assert summary.adaptation_status.domino_shift_ready is False

            # AI insight
            assert "Chưa đủ dữ liệu học tập" in summary.ai_insight.message
            assert summary.ai_insight.efficiency_growth_pct == 0.0
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()


@pytest.mark.asyncio
async def test_dashboard_summary_active_user_real_data() -> None:
    """Test Case 2: Người dùng có lộ trình đang hoạt động và buổi học thật.

    Kiểm tra tính toán KPI (monthly_hours, streak, adherence), today queue và
    schedule blocks khớp chính xác dữ liệu trong DB.
    """
    user_id: UUID = uuid7()
    today = date.today()
    now = datetime.now(UTC)

    async with async_session_factory() as session:
        user = UserORM(
            id=user_id,
            email=f"active_learner_{user_id.hex[:8]}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="Active Learner",
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="PREMIUM",
            is_locked=False,
        )
        session.add(user)

        goal = GoalORM(
            user_id=user_id,
            title="Làm chủ Go & Hexagonal Architecture",
            raw_description="Học thiết kế hệ thống chuyên sâu",
            target_date=today + timedelta(days=60),
            status="ACTIVE",
        )
        session.add(goal)
        await session.flush()

        roadmap = RoadmapORM(
            user_id=user_id,
            goal_id=goal.id,
            title="Go Hexagonal Architecture & High-Throughput",
            status="ACTIVE",
            start_date=today - timedelta(days=14),
            target_date=today + timedelta(days=45),
        )
        session.add(roadmap)
        await session.flush()

        milestone = MilestoneORM(
            roadmap_id=roadmap.id,
            sequence_order=1,
            title="Chặng 1: Domain Models & Ports",
            status="IN_PROGRESS",
        )
        session.add(milestone)
        await session.flush()

        official_sched = OfficialScheduleORM(
            roadmap_id=roadmap.id,
            total_sessions=20,
            total_planned_minutes=2400,  # 40 hours over ~8 weeks => ~5 hrs/wk
        )
        session.add(official_sched)
        await session.flush()

        # Task 1: Completed
        task_comp = TaskORM(
            roadmap_id=roadmap.id,
            milestone_id=milestone.id,
            title="Thiết kế Aggregate Root trong Go",
            estimated_minutes=90,
            status="COMPLETED",
            scheduled_date=today - timedelta(days=1),
            completed_at=now - timedelta(days=1),
        )
        # Task 2: Scheduled today
        task_today = TaskORM(
            roadmap_id=roadmap.id,
            milestone_id=milestone.id,
            title="Triển khai Outbox Worker và Event Dispatcher",
            estimated_minutes=60,
            status="TODO",
            scheduled_date=today,
            scheduled_start=datetime.combine(today, datetime.min.time(), tzinfo=UTC)
            + timedelta(hours=9),
            scheduled_end=datetime.combine(today, datetime.min.time(), tzinfo=UTC)
            + timedelta(hours=10),
        )
        session.add_all([task_comp, task_today])
        await session.flush()

        # Schedule block for today
        sched_block = ScheduleBlockORM(
            roadmap_id=roadmap.id,
            official_schedule_id=official_sched.id,
            task_id=task_today.id,
            sequence_in_task=1,
            block_type="STUDY",
            block_date=today,
            start_time=now.replace(hour=9, minute=0, second=0, microsecond=0),
            end_time=now.replace(hour=10, minute=0, second=0, microsecond=0),
            scheduled_duration_minutes=60,
            status="PLANNED",
            placement_rationale="Buổi học lập trình chuyên sâu",
        )
        session.add(sched_block)

        # Study session completed yesterday
        session_past = StudySessionORM(
            user_id=user_id,
            roadmap_id=roadmap.id,
            started_at=now - timedelta(days=1, hours=2),
            ended_at=now - timedelta(days=1, hours=1),
            planned_minutes=60,
            actual_minutes=60,
            status="COMPLETED",
            last_heartbeat_at=now - timedelta(days=1, hours=1),
        )
        # Study session completed today
        session_today = StudySessionORM(
            user_id=user_id,
            roadmap_id=roadmap.id,
            started_at=now - timedelta(hours=3),
            ended_at=now - timedelta(hours=2),
            planned_minutes=60,
            actual_minutes=60,
            status="COMPLETED",
            last_heartbeat_at=now - timedelta(hours=2),
        )
        session.add_all([session_past, session_today])

        # Weekly Review
        intel_repo = SqlAlchemyEvaluationIntelligenceRepository(session)
        await intel_repo.create_weekly_review(
            roadmap_id=roadmap.id,
            user_id=user_id,
            period_start=today - timedelta(days=7),
            period_end=today,
            reflection={
                "strengths_feedback": "Khả năng duy trì nhịp độ giải quyết bài tập rất tốt.",
                "bottlenecks_feedback": "Cần lưu ý phân bổ thời gian nghỉ giữa các phiên dài.",
                "action_recommendations": "Tiếp tục duy trì học vào khung giờ sáng.",
                "quantitative_summary": {
                    "efficiency_growth_pct": 16.5,
                    "peak_hours": "09:00 - 11:00",
                },
                "user_reflection_payload": {},
            },
        )

        await session.commit()

    try:
        async with async_session_factory() as session:
            planning_port = PlanningDashboardAdapter(session)
            execution_port = ExecutionDashboardAdapter(session)
            intel_repo = SqlAlchemyEvaluationIntelligenceRepository(session)

            use_case = GetDashboardSummaryUseCase(
                planning_port=planning_port,
                execution_port=execution_port,
                intelligence_repo=intel_repo,
            )

            summary = await use_case.execute(user_id)

            # KPIs check
            assert summary.kpi.monthly_hours >= 2.0
            assert summary.kpi.target_hours > 0.0
            assert summary.kpi.streak_days >= 2
            assert summary.kpi.completed_pomodoro_count >= 2
            assert summary.kpi.deep_work_hours >= 2.0

            # Active roadmaps check
            assert len(summary.active_roadmaps) == 1
            rd = summary.active_roadmaps[0]
            assert "Go Hexagonal Architecture" in rd.title
            assert rd.completed_tasks == 1
            assert rd.total_tasks == 2
            assert rd.progress_pct == 50.0
            assert "Outbox Worker" in rd.next_task_title

            # Today queue check
            assert len(summary.today_queue) == 1
            q_task = summary.today_queue[0]
            assert "Outbox Worker" in q_task.title
            assert q_task.status == "READY"
            assert q_task.pomodoro_estimate == 3

            # Visual schedule blocks check
            assert len(summary.schedule_blocks) >= 1
            assert any("Outbox Worker" in b.title for b in summary.schedule_blocks)

            # AI insight check
            assert "Duy trì nhịp học đều" in summary.ai_insight.message
            assert summary.ai_insight.efficiency_growth_pct == 10.0
            assert summary.ai_insight.peak_hours == "08:30 - 10:30"

            # Adaptation status check (no overdue tasks)
            assert summary.adaptation_status.is_balanced is True
            assert summary.adaptation_status.domino_shift_ready is False
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()


@pytest.mark.asyncio
async def test_dashboard_summary_overdue_tasks_adaptation() -> None:
    """Test Case 3: Người dùng có nhiệm vụ quá hạn (Overdue Tasks).

    Xác nhận adaptation_status.is_balanced == False và domino_shift_ready == True.
    """
    user_id: UUID = uuid7()
    today = date.today()

    async with async_session_factory() as session:
        user = UserORM(
            id=user_id,
            email=f"overdue_learner_{user_id.hex[:8]}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="Overdue Learner",
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE",
            is_locked=False,
        )
        session.add(user)

        goal = GoalORM(
            user_id=user_id,
            title="Luyện thi IELTS",
            raw_description="IELTS 7.5 Target",
            target_date=today + timedelta(days=90),
            status="ACTIVE",
        )
        session.add(goal)
        await session.flush()

        roadmap = RoadmapORM(
            user_id=user_id,
            goal_id=goal.id,
            title="IELTS Academic 7.5 - Target Band Mastery",
            status="ACTIVE",
            start_date=today - timedelta(days=30),
            target_date=today + timedelta(days=60),
        )
        session.add(roadmap)
        await session.flush()

        milestone = MilestoneORM(
            roadmap_id=roadmap.id,
            sequence_order=1,
            title="IELTS Writing Phase",
            status="IN_PROGRESS",
        )
        session.add(milestone)
        await session.flush()

        # Overdue tasks: scheduled in past with status TODO
        task_overdue_1 = TaskORM(
            roadmap_id=roadmap.id,
            milestone_id=milestone.id,
            title="Writing Task 2 Essay Outline",
            estimated_minutes=60,
            status="TODO",
            scheduled_date=today - timedelta(days=3),
        )
        task_overdue_2 = TaskORM(
            roadmap_id=roadmap.id,
            milestone_id=milestone.id,
            title="Writing Task 2 Academic Vocabulary",
            estimated_minutes=45,
            status="IN_PROGRESS",
            scheduled_date=today - timedelta(days=1),
        )
        session.add_all([task_overdue_1, task_overdue_2])
        await session.commit()

    try:
        async with async_session_factory() as session:
            planning_port = PlanningDashboardAdapter(session)
            execution_port = ExecutionDashboardAdapter(session)
            intel_repo = SqlAlchemyEvaluationIntelligenceRepository(session)

            use_case = GetDashboardSummaryUseCase(
                planning_port=planning_port,
                execution_port=execution_port,
                intelligence_repo=intel_repo,
            )

            summary = await use_case.execute(user_id)

            # Adaptation status check
            assert summary.adaptation_status.is_balanced is False
            assert summary.adaptation_status.domino_shift_ready is True
            assert "2 nhiệm vụ trễ hạn" in summary.adaptation_status.message
            assert "Domino Shift" in summary.adaptation_status.message
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()
