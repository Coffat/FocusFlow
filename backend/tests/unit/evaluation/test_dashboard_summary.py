import pytest
from fastapi.testclient import TestClient
from uuid6 import uuid7

from src.evaluation.application.dtos.dashboard_dtos import DashboardSummaryResponseDTO
from src.evaluation.application.use_cases.dashboard_summary import (
    GetDashboardSummaryUseCase,
)
from src.evaluation.presentation.deps import get_current_evaluation_learner_id
from src.main import app


@pytest.mark.asyncio
async def test_get_dashboard_summary_use_case_returns_valid_data() -> None:
    # Arrange
    user_id = uuid7()
    use_case = GetDashboardSummaryUseCase()

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
    assert len(summary.today_queue) >= 2
    assert any(q.status == "READY" for q in summary.today_queue)

    # AI Insight & Adaptation status check
    assert "FocusFlow AI" in summary.ai_insight.model_version
    assert summary.adaptation_status.is_balanced is True
    assert summary.adaptation_status.domino_shift_ready is True

    # Visual schedule blocks check
    assert len(summary.schedule_blocks) >= 5
    assert all(b.pomodoro_count > 0 for b in summary.schedule_blocks)
    assert all(b.duration_minutes > 0 for b in summary.schedule_blocks)


def test_dashboard_summary_endpoint_authenticated() -> None:
    test_user_id = uuid7()
    app.dependency_overrides[get_current_evaluation_learner_id] = lambda: test_user_id

    try:
        client = TestClient(app)
        response = client.get("/api/v1/evaluation/dashboard-summary")

        assert response.status_code == 200
        data = response.json()

        assert "kpi" in data
        assert data["kpi"]["monthly_hours"] == 42.5
        assert data["kpi"]["streak_days"] == 12
        assert data["kpi"]["adherence_rate_pct"] == 91.2

        assert "active_roadmaps" in data
        assert len(data["active_roadmaps"]) == 2
        assert data["active_roadmaps"][0]["code"] == "RD-IELTS-75"

        assert "today_queue" in data
        assert len(data["today_queue"]) >= 2

        assert "schedule_blocks" in data
        assert len(data["schedule_blocks"]) >= 5

        assert "ai_insight" in data
        assert "adaptation_status" in data
        assert data["adaptation_status"]["is_balanced"] is True
    finally:
        app.dependency_overrides.pop(get_current_evaluation_learner_id, None)


def test_dashboard_summary_endpoint_unauthorized() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/evaluation/dashboard-summary")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"
