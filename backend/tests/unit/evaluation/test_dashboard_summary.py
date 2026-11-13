from datetime import date
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from uuid6 import uuid7

from src.evaluation.application.dtos.dashboard_dtos import DashboardSummaryResponseDTO
from src.evaluation.application.ports.intelligence_repository_port import (
    EvaluationIntelligenceRepositoryPort,
)
from src.evaluation.application.use_cases.dashboard_summary import (
    GetDashboardSummaryUseCase,
)
from src.evaluation.domain.models.intelligence import WeeklyReview
from src.evaluation.presentation.deps import get_current_evaluation_learner_id
from src.execution.public_api import (
    ExecutionDashboardQueryPort,
    ExecutionDayStudyDTO,
    ExecutionKpiStatsDTO,
    ExecutionTodayTaskDTO,
)
from src.main import app
from src.planning.public_api import (
    PlanningActiveRoadmapDTO,
    PlanningDashboardQueryPort,
    PlanningDashboardScheduleBlockDTO,
)


@pytest.mark.asyncio
async def test_get_dashboard_summary_use_case_returns_valid_data() -> None:
    # Arrange
    user_id = uuid7()
    ielts_id = uuid7()
    go_id = uuid7()

    planning_port = AsyncMock(spec=PlanningDashboardQueryPort)
    planning_port.get_active_roadmaps_for_user.return_value = [
        PlanningActiveRoadmapDTO(
            id=ielts_id,
            code="RD-IELTS-75",
            title="IELTS Academic 7.5 - Target Band Mastery",
            commitment_hours_per_week=12.0,
            deadline="2026-12-20",
            completed_tasks=28,
            total_tasks=40,
            progress_pct=70.0,
            next_task_code="TSK-WRT-02",
            next_task_title="Task 2 Academic Essay: Causes and Solutions",
        ),
        PlanningActiveRoadmapDTO(
            id=go_id,
            code="RD-GO-HEX",
            title="Go Hexagonal Architecture & High-Throughput Microservices",
            commitment_hours_per_week=10.0,
            deadline="2027-01-15",
            completed_tasks=14,
            total_tasks=35,
            progress_pct=40.0,
            next_task_code="TSK-GOLANG-08",
            next_task_title="Implement Domain Events and Outbox Worker in Go",
        ),
    ]
    planning_port.get_monthly_target_hours.return_value = 50.0
    planning_port.get_week_schedule_blocks.return_value = [
        PlanningDashboardScheduleBlockDTO(
            id=uuid7(),
            day_of_week=1,
            day_label="Thứ Hai",
            start_time="08:30",
            end_time="10:00",
            title="IELTS Reading Passage 3 Analysis",
            category="Language",
            status="COMPLETED",
            pomodoro_count=3,
            duration_minutes=90,
            roadmap_code="RD-IELTS-75",
        ),
        PlanningDashboardScheduleBlockDTO(
            id=uuid7(),
            day_of_week=2,
            day_label="Thứ Ba",
            start_time="14:00",
            end_time="15:30",
            title="Go Interfaces & Mocking Patterns",
            category="Engineering",
            status="COMPLETED",
            pomodoro_count=3,
            duration_minutes=90,
            roadmap_code="RD-GO-HEX",
        ),
    ]

    execution_port = AsyncMock(spec=ExecutionDashboardQueryPort)
    execution_port.get_today_queue.return_value = [
        ExecutionTodayTaskDTO(
            id=uuid7(),
            task_code="TSK-WRT-02",
            title="Task 2 Academic Essay: Causes and Solutions",
            roadmap_title="IELTS Academic 7.5 - Target Band Mastery",
            scheduled_time="08:30 - 10:00",
            pomodoro_estimate=3,
            duration_minutes=90,
            status="READY",
        ),
        ExecutionTodayTaskDTO(
            id=uuid7(),
            task_code="TSK-GOLANG-08",
            title="Implement Domain Events and Outbox Worker in Go",
            roadmap_title="Go Hexagonal Architecture & High-Throughput Microservices",
            scheduled_time="14:00 - 15:30",
            pomodoro_estimate=3,
            duration_minutes=90,
            status="SCHEDULED",
        ),
    ]
    execution_port.get_7day_study_distribution.return_value = [
        ExecutionDayStudyDTO(
            day_date=date.today(), day_label="Mon", study_hours=2.5, is_today=False
        ),
        ExecutionDayStudyDTO(
            day_date=date.today(), day_label="Tue", study_hours=3.0, is_today=False
        ),
        ExecutionDayStudyDTO(
            day_date=date.today(), day_label="Wed", study_hours=3.5, is_today=True
        ),
        ExecutionDayStudyDTO(
            day_date=date.today(), day_label="Thu", study_hours=2.0, is_today=False
        ),
        ExecutionDayStudyDTO(
            day_date=date.today(), day_label="Fri", study_hours=3.0, is_today=False
        ),
        ExecutionDayStudyDTO(
            day_date=date.today(), day_label="Sat", study_hours=4.5, is_today=False
        ),
        ExecutionDayStudyDTO(
            day_date=date.today(), day_label="Sun", study_hours=4.0, is_today=False
        ),
    ]
    execution_port.get_execution_kpis.return_value = ExecutionKpiStatsDTO(
        monthly_study_seconds=153000,  # 42.5 hours
        deep_work_seconds=129600,  # 36.0 hours
        completed_pomodoro_count=85,
        streak_days=12,
        personal_best_streak=18,
        streak_history_last_7_days=[True] * 7,
        adherence_rate_pct=91.2,
        adherence_delta_pct=4.5,
        overdue_tasks_count=0,
    )

    intelligence_repo = AsyncMock(spec=EvaluationIntelligenceRepositoryPort)
    intelligence_repo.latest_weekly_review.return_value = WeeklyReview(
        roadmap_id=ielts_id,
        user_id=user_id,
        period_start=date.today(),
        period_end=date.today(),
        quantitative_summary={"efficiency_growth_pct": 14.8, "peak_hours": "08:30 - 10:30"},
        strengths_feedback="Khả năng tập trung đạt đỉnh trong khung 08:30 - 10:30 sáng.",
        bottlenecks_feedback="",
        action_recommendations="",
        user_reflection_payload={},
    )

    use_case = GetDashboardSummaryUseCase(
        planning_port=planning_port,
        execution_port=execution_port,
        intelligence_repo=intelligence_repo,
    )

    # Act
    summary = await use_case.execute(user_id)

    # Assert
    assert isinstance(summary, DashboardSummaryResponseDTO)

    # KPIs check
    assert summary.kpi.monthly_hours == 42.5
    assert summary.kpi.target_hours == 50.0
    assert summary.kpi.monthly_progress_pct == 85.0
    assert summary.kpi.streak_days == 12
    assert summary.kpi.personal_best_streak == 18
    assert summary.kpi.adherence_rate_pct == 91.2
    assert len(summary.kpi.streak_history_last_7_days) == 7

    # Study distribution check
    assert len(summary.study_distribution) == 7
    days = [d.day_label for d in summary.study_distribution]
    assert days == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    assert any(d.is_today for d in summary.study_distribution)

    # Active roadmaps check
    assert len(summary.active_roadmaps) == 2
    codes = [r.code for r in summary.active_roadmaps]
    assert "RD-IELTS-75" in codes
    assert "RD-GO-HEX" in codes
    ielts = next(r for r in summary.active_roadmaps if r.code == "RD-IELTS-75")
    assert "IELTS Academic 7.5" in ielts.title
    assert ielts.progress_pct == 70.0
    assert ielts.completed_tasks == 28

    # Today queue check
    assert len(summary.today_queue) == 2
    assert any(q.status == "READY" for q in summary.today_queue)

    # AI Insight & Adaptation status check
    assert "FocusFlow AI" in summary.ai_insight.model_version
    assert summary.ai_insight.efficiency_growth_pct == 14.8
    assert summary.adaptation_status.is_balanced is True
    assert summary.adaptation_status.domino_shift_ready is False

    # Visual schedule blocks check
    assert len(summary.schedule_blocks) == 2
    assert all(b.pomodoro_count > 0 for b in summary.schedule_blocks)
    assert all(b.duration_minutes > 0 for b in summary.schedule_blocks)


def test_dashboard_summary_endpoint_authenticated() -> None:
    test_user_id = UUID("00000000-0000-0000-0000-000000000001")
    app.dependency_overrides[get_current_evaluation_learner_id] = lambda: test_user_id

    try:
        client = TestClient(app)
        response = client.get("/api/v1/evaluation/dashboard-summary")

        assert response.status_code == 200
        data = response.json()

        assert "kpi" in data
        assert "monthly_hours" in data["kpi"]
        assert "streak_days" in data["kpi"]
        assert "active_roadmaps" in data
        assert "today_queue" in data
        assert "schedule_blocks" in data
        assert "ai_insight" in data
        assert "adaptation_status" in data
        assert "study_distribution" in data
    finally:
        app.dependency_overrides.pop(get_current_evaluation_learner_id, None)


def test_dashboard_summary_endpoint_unauthorized() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/evaluation/dashboard-summary")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"
