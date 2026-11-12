from datetime import date, timedelta
from uuid import UUID

from src.evaluation.application.dtos.dashboard_dtos import (
    DashboardActiveRoadmapDTO,
    DashboardAdaptationStatusDTO,
    DashboardAiInsightDTO,
    DashboardKpiDTO,
    DashboardScheduleBlockDTO,
    DashboardSummaryResponseDTO,
    DashboardTodayQueueItemDTO,
    DayStudyDistributionDTO,
)
from src.evaluation.application.ports.intelligence_repository_port import (
    EvaluationIntelligenceRepositoryPort,
)
from src.execution.public_api import ExecutionDashboardQueryPort
from src.planning.public_api import PlanningDashboardQueryPort


class GetDashboardSummaryUseCase:
    """Use case cung cấp dữ liệu tổng quan bảng điều khiển (User Dashboard) từ dữ liệu thực tế."""

    def __init__(
        self,
        planning_port: PlanningDashboardQueryPort,
        execution_port: ExecutionDashboardQueryPort,
        intelligence_repo: EvaluationIntelligenceRepositoryPort,
    ) -> None:
        self._planning_port = planning_port
        self._execution_port = execution_port
        self._intelligence_repo = intelligence_repo

    async def execute(self, user_id: UUID) -> DashboardSummaryResponseDTO:
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        # 1. Fetch data from Planning & Execution ports concurrently or sequentially
        active_roadmaps_raw = await self._planning_port.get_active_roadmaps_for_user(user_id)
        target_hours = await self._planning_port.get_monthly_target_hours(user_id)
        schedule_blocks_raw = await self._planning_port.get_week_schedule_blocks(
            user_id, start_of_week, end_of_week
        )

        today_queue_raw = await self._execution_port.get_today_queue(user_id, today)
        study_distribution_raw = await self._execution_port.get_7day_study_distribution(
            user_id, today
        )
        kpi_stats = await self._execution_port.get_execution_kpis(user_id, today)

        latest_weekly_review = await self._intelligence_repo.latest_weekly_review(user_id)

        # 2. Build Core KPIs
        monthly_hours = round(kpi_stats.monthly_study_seconds / 3600.0, 1)
        deep_work_hours = round(kpi_stats.deep_work_seconds / 3600.0, 1)
        monthly_progress_pct = (
            round((monthly_hours / target_hours) * 100.0, 1) if target_hours > 0.0 else 0.0
        )

        kpi = DashboardKpiDTO(
            monthly_hours=monthly_hours,
            target_hours=target_hours,
            monthly_progress_pct=monthly_progress_pct,
            streak_days=kpi_stats.streak_days,
            personal_best_streak=kpi_stats.personal_best_streak,
            streak_history_last_7_days=kpi_stats.streak_history_last_7_days,
            adherence_rate_pct=kpi_stats.adherence_rate_pct,
            adherence_delta_pct=kpi_stats.adherence_delta_pct,
            completed_pomodoro_count=kpi_stats.completed_pomodoro_count,
            deep_work_hours=deep_work_hours,
        )

        # 3. Build 7-Day Study Distribution
        study_distribution = [
            DayStudyDistributionDTO(
                day_label=d.day_label,
                hours=d.study_hours,
                is_today=d.is_today,
            )
            for d in study_distribution_raw
        ]

        # 4. Build Active Roadmaps
        active_roadmaps = [
            DashboardActiveRoadmapDTO(
                id=r.id,
                code=r.code,
                title=r.title,
                commitment_hours_per_week=r.commitment_hours_per_week,
                deadline=r.deadline or "",
                completed_tasks=r.completed_tasks,
                total_tasks=r.total_tasks,
                progress_pct=r.progress_pct,
                next_task_code=r.next_task_code or "",
                next_task_title=r.next_task_title or "",
            )
            for r in active_roadmaps_raw
        ]

        # 5. Build Today Queue Items
        today_queue = [
            DashboardTodayQueueItemDTO(
                id=q.id,
                task_code=q.task_code,
                title=q.title,
                roadmap_title=q.roadmap_title,
                scheduled_time=q.scheduled_time,
                pomodoro_estimate=q.pomodoro_estimate,
                duration_minutes=q.duration_minutes,
                status=q.status,
            )
            for q in today_queue_raw
        ]

        # 6. Build AI Insight
        if latest_weekly_review is not None:
            message = (
                latest_weekly_review.strengths_feedback
                or "Tiến độ học tập đang được duy trì ổn định."
            )
            efficiency_growth_pct = float(
                latest_weekly_review.quantitative_summary.get("efficiency_growth_pct", 10.0)
            )
            peak_hours = str(
                latest_weekly_review.quantitative_summary.get("peak_hours", "08:30 - 10:30")
            )
            ai_insight = DashboardAiInsightDTO(
                model_version="FocusFlow AI v2.4 (Gemini Pro H-SRL)",
                message=message,
                peak_hours=peak_hours,
                efficiency_growth_pct=efficiency_growth_pct,
            )
        else:
            ai_insight = DashboardAiInsightDTO(
                model_version="FocusFlow AI v2.4 (Gemini Pro H-SRL)",
                message=(
                    "Chưa đủ dữ liệu học tập (yêu cầu hoàn thành tối thiểu "
                    "buổi học đầu tiên để kích hoạt AI Insight)"
                ),
                peak_hours="--:--",
                efficiency_growth_pct=0.0,
            )

        # 7. Build Adaptation Status
        if kpi_stats.overdue_tasks_count > 0:
            adaptation_status = DashboardAdaptationStatusDTO(
                is_balanced=False,
                message=(
                    f"Có {kpi_stats.overdue_tasks_count} nhiệm vụ trễ hạn, "
                    f"cần điều chỉnh lịch (Domino Shift)."
                ),
                domino_shift_ready=True,
            )
        else:
            adaptation_status = DashboardAdaptationStatusDTO(
                is_balanced=True,
                message="Lộ trình đang cân bằng tối ưu. Không có khối học bị xung đột hoặc trễ hạn.",
                domino_shift_ready=False,
            )

        # 8. Build Visual Schedule Blocks
        schedule_blocks = [
            DashboardScheduleBlockDTO(
                id=b.id,
                day_of_week=b.day_of_week,
                day_label=b.day_label,
                start_time=b.start_time,
                end_time=b.end_time,
                title=b.title,
                category=b.category,
                status=b.status,
                pomodoro_count=b.pomodoro_count,
                duration_minutes=b.duration_minutes,
                roadmap_code=b.roadmap_code,
                description=b.description,
            )
            for b in schedule_blocks_raw
        ]

        return DashboardSummaryResponseDTO(
            kpi=kpi,
            study_distribution=study_distribution,
            active_roadmaps=active_roadmaps,
            today_queue=today_queue,
            ai_insight=ai_insight,
            adaptation_status=adaptation_status,
            schedule_blocks=schedule_blocks,
        )
