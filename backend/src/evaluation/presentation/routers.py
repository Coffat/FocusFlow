from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.evaluation.application.dtos.dashboard_dtos import (
    DashboardSummaryResponseDTO,
)
from src.evaluation.application.dtos.intelligence import (
    GenerateProofResponseDTO,
    GenerateWeeklyReviewRequestDTO,
    MilestoneProofResponseDTO,
    SubmitProofRequestDTO,
    WeeklyReviewResponseDTO,
)
from src.evaluation.application.ports.intelligence_repository_port import (
    DuplicateWeeklyReviewConflictError,
)
from src.evaluation.application.use_cases.analytics import (
    GetAnalyticsSummaryUseCase,
    GetWeeklyAnalyticsUseCase,
)
from src.evaluation.application.use_cases.dashboard_summary import (
    GetDashboardSummaryUseCase,
)
from src.evaluation.application.use_cases.intelligence import (
    EvaluationResourceNotFoundError,
    GenerateMilestoneProofUseCase,
    GenerateWeeklyReviewUseCase,
    GetLatestWeeklyReviewUseCase,
    SubmitMilestoneProofUseCase,
)
from src.evaluation.presentation.deps import (
    get_analytics_summary_use_case,
    get_current_evaluation_learner_id,
    get_dashboard_summary_use_case,
    get_generate_proof_use_case,
    get_generate_weekly_review_use_case,
    get_latest_weekly_review_use_case,
    get_submit_proof_use_case,
    get_weekly_analytics_use_case,
)
from src.evaluation.presentation.schemas.analytics_schemas import (
    AnalyticsDailyMetricResponse,
    AnalyticsSummaryResponse,
    AnalyticsWeeklyResponse,
)

router = APIRouter(prefix="/api/v1/evaluation", tags=["Evaluation & Analytics"])
analytics_router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/status")
async def get_evaluation_context_status() -> dict[str, str]:
    """Bounded Context 4 health/status endpoint (UC-14..UC-17, UC-19)."""
    return {"context": "evaluation", "status": "ready"}


@router.get("/dashboard-summary", response_model=DashboardSummaryResponseDTO)
async def get_dashboard_summary(
    user_id: UUID = Depends(get_current_evaluation_learner_id),
    use_case: GetDashboardSummaryUseCase = Depends(get_dashboard_summary_use_case),
) -> DashboardSummaryResponseDTO:
    """Trả về tổng quan bảng điều khiển Dashboard cá nhân hóa của người học."""
    return await use_case.execute(user_id)


@router.post(
    "/milestones/{milestone_id}/proofs/generate-jobs",
    response_model=GenerateProofResponseDTO,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_milestone_proof(
    milestone_id: UUID,
    user_id: UUID = Depends(get_current_evaluation_learner_id),
    use_case: GenerateMilestoneProofUseCase = Depends(get_generate_proof_use_case),
) -> GenerateProofResponseDTO:
    try:
        return await use_case.execute(user_id, milestone_id)
    except EvaluationResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Milestone not found") from exc


@router.post(
    "/milestones/{milestone_id}/proofs/{proof_id}/submit",
    response_model=MilestoneProofResponseDTO,
)
async def submit_milestone_proof(
    milestone_id: UUID,
    proof_id: UUID,
    request: SubmitProofRequestDTO,
    user_id: UUID = Depends(get_current_evaluation_learner_id),
    use_case: SubmitMilestoneProofUseCase = Depends(get_submit_proof_use_case),
) -> MilestoneProofResponseDTO:
    try:
        return await use_case.execute(user_id, milestone_id, proof_id, request)
    except EvaluationResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Proof not found") from exc


@router.post(
    "/weekly-reviews/generate-jobs",
    response_model=WeeklyReviewResponseDTO,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_weekly_review(
    request: GenerateWeeklyReviewRequestDTO,
    user_id: UUID = Depends(get_current_evaluation_learner_id),
    use_case: GenerateWeeklyReviewUseCase = Depends(get_generate_weekly_review_use_case),
) -> WeeklyReviewResponseDTO:
    try:
        return await use_case.execute(user_id, request)
    except DuplicateWeeklyReviewConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except EvaluationResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Roadmap not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/weekly-reviews/latest", response_model=WeeklyReviewResponseDTO)
async def latest_weekly_review(
    user_id: UUID = Depends(get_current_evaluation_learner_id),
    use_case: GetLatestWeeklyReviewUseCase = Depends(get_latest_weekly_review_use_case),
) -> WeeklyReviewResponseDTO:
    try:
        return await use_case.execute(user_id)
    except EvaluationResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Weekly review not found") from exc


@analytics_router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get quantitative analytics summary including WRLS, Adherence & Completion Rate (UC-19)",
)
async def get_analytics_summary(
    user_id: UUID = Depends(get_current_evaluation_learner_id),
    use_case: GetAnalyticsSummaryUseCase = Depends(get_analytics_summary_use_case),
) -> AnalyticsSummaryResponse:
    dto = await use_case.execute(user_id)
    return AnalyticsSummaryResponse(
        total_focused_hours=dto.total_focused_hours,
        weekly_study_hours=dto.weekly_study_hours,
        task_completion_rate=dto.task_completion_rate,
        plan_adherence_rate=dto.plan_adherence_rate,
        weekly_recovered_learning_sessions=dto.weekly_recovered_learning_sessions,
        completed_tasks_count=dto.completed_tasks_count,
        total_tasks_count=dto.total_tasks_count,
        active_streak_days=dto.active_streak_days,
        average_focus_score=dto.average_focus_score,
        daily_metrics=[
            AnalyticsDailyMetricResponse(
                date=m.date,
                day_label=m.day_label,
                minutes_studied=m.minutes_studied,
                pomodoros_completed=m.pomodoros_completed,
                sessions_count=m.sessions_count,
                is_today=m.is_today,
            )
            for m in dto.daily_metrics
        ],
    )


@analytics_router.get(
    "/weekly",
    response_model=AnalyticsWeeklyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get 7-day breakdown, WRLS, and adherence stats (UC-19)",
)
async def get_weekly_analytics(
    user_id: UUID = Depends(get_current_evaluation_learner_id),
    use_case: GetWeeklyAnalyticsUseCase = Depends(get_weekly_analytics_use_case),
    week_start: Annotated[date | None, Query()] = None,
) -> AnalyticsWeeklyResponse:
    dto = await use_case.execute(user_id, week_start=week_start)
    return AnalyticsWeeklyResponse(
        week_start=dto.week_start,
        week_end=dto.week_end,
        total_focused_hours=dto.total_focused_hours,
        completed_sessions_count=dto.completed_sessions_count,
        completed_tasks_count=dto.completed_tasks_count,
        total_scheduled_tasks_count=dto.total_scheduled_tasks_count,
        task_completion_rate=dto.task_completion_rate,
        plan_adherence_rate=dto.plan_adherence_rate,
        weekly_recovered_learning_sessions=dto.weekly_recovered_learning_sessions,
        daily_breakdown=[
            AnalyticsDailyMetricResponse(
                date=m.date,
                day_label=m.day_label,
                minutes_studied=m.minutes_studied,
                pomodoros_completed=m.pomodoros_completed,
                sessions_count=m.sessions_count,
                is_today=m.is_today,
            )
            for m in dto.daily_breakdown
        ],
    )
