from uuid import UUID, uuid5

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


class GetDashboardSummaryUseCase:
    """Use case cung cấp dữ liệu tổng quan bảng điều khiển (User Dashboard).

    Trả về các chỉ số học tập trọng yếu (KPIs), phân bổ giờ học, danh sách lộ trình đang kích hoạt
    (IELTS Academic 7.5, Go Hexagonal Backend), hàng đợi nhiệm vụ hôm nay và lịch học phân bổ.
    """

    def __init__(self) -> None:
        pass

    async def execute(self, user_id: UUID) -> DashboardSummaryResponseDTO:
        # 1. Core KPIs
        kpi = DashboardKpiDTO(
            monthly_hours=42.5,
            target_hours=50.0,
            monthly_progress_pct=85.0,
            streak_days=12,
            personal_best_streak=18,
            streak_history_last_7_days=[True, True, True, True, True, True, True],
            adherence_rate_pct=91.2,
            adherence_delta_pct=4.5,
            completed_pomodoro_count=85,
            deep_work_hours=36.0,
        )

        # 2. 7-Day Study Distribution
        study_distribution = [
            DayStudyDistributionDTO(day_label="Mon", hours=2.5, is_today=False),
            DayStudyDistributionDTO(day_label="Tue", hours=3.0, is_today=False),
            DayStudyDistributionDTO(day_label="Wed", hours=3.5, is_today=True),
            DayStudyDistributionDTO(day_label="Thu", hours=2.0, is_today=False),
            DayStudyDistributionDTO(day_label="Fri", hours=3.0, is_today=False),
            DayStudyDistributionDTO(day_label="Sat", hours=4.5, is_today=False),
            DayStudyDistributionDTO(day_label="Sun", hours=4.0, is_today=False),
        ]

        # 3. Active Roadmaps
        ielts_id = uuid5(user_id, "roadmap-ielts-75")
        go_id = uuid5(user_id, "roadmap-go-hex")

        active_roadmaps = [
            DashboardActiveRoadmapDTO(
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
            DashboardActiveRoadmapDTO(
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

        # 4. Today Queue Items
        today_queue = [
            DashboardTodayQueueItemDTO(
                id=uuid5(user_id, "task-queue-1"),
                task_code="TSK-WRT-02",
                title="Task 2 Academic Essay: Causes and Solutions",
                roadmap_title="IELTS Academic 7.5 - Target Band Mastery",
                scheduled_time="08:30 - 10:00",
                pomodoro_estimate=3,
                duration_minutes=90,
                status="READY",
            ),
            DashboardTodayQueueItemDTO(
                id=uuid5(user_id, "task-queue-2"),
                task_code="TSK-GOLANG-08",
                title="Implement Domain Events and Outbox Worker in Go",
                roadmap_title="Go Hexagonal Architecture & High-Throughput Microservices",
                scheduled_time="14:00 - 15:30",
                pomodoro_estimate=3,
                duration_minutes=90,
                status="SCHEDULED",
            ),
            DashboardTodayQueueItemDTO(
                id=uuid5(user_id, "task-queue-3"),
                task_code="TSK-VOCAB-04",
                title="Lexical Resource Drill: Education & Society Topic",
                roadmap_title="IELTS Academic 7.5 - Target Band Mastery",
                scheduled_time="19:30 - 20:30",
                pomodoro_estimate=2,
                duration_minutes=60,
                status="SCHEDULED",
            ),
        ]

        # 5. AI Insight
        ai_insight = DashboardAiInsightDTO(
            model_version="FocusFlow AI v2.4 (Gemini Pro H-SRL)",
            message=(
                "Khả năng tập trung đạt đỉnh trong khung 08:30 - 10:30 sáng. "
                "Tỷ lệ hoàn thành Pomodoro tăng 18.5% khi ôn tập IELTS trước giờ lập trình."
            ),
            peak_hours="08:30 - 10:30",
            efficiency_growth_pct=14.8,
        )

        # 6. Adaptation Status
        adaptation_status = DashboardAdaptationStatusDTO(
            is_balanced=True,
            message="Lộ trình đang cân bằng tối ưu. Không có khối học bị xung đột hoặc trễ hạn.",
            domino_shift_ready=True,
        )

        # 7. Visual Schedule Blocks
        schedule_blocks = [
            DashboardScheduleBlockDTO(
                id=uuid5(user_id, "block-mon-1"),
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
            DashboardScheduleBlockDTO(
                id=uuid5(user_id, "block-tue-1"),
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
            DashboardScheduleBlockDTO(
                id=uuid5(user_id, "block-wed-1"),
                day_of_week=3,
                day_label="Thứ Tư",
                start_time="08:30",
                end_time="10:00",
                title="Task 2 Academic Essay: Causes and Solutions",
                category="Language",
                status="IN_PROGRESS",
                pomodoro_count=3,
                duration_minutes=90,
                roadmap_code="RD-IELTS-75",
            ),
            DashboardScheduleBlockDTO(
                id=uuid5(user_id, "block-wed-2"),
                day_of_week=3,
                day_label="Thứ Tư",
                start_time="14:00",
                end_time="15:30",
                title="Implement Domain Events and Outbox Worker in Go",
                category="Engineering",
                status="SCHEDULED",
                pomodoro_count=3,
                duration_minutes=90,
                roadmap_code="RD-GO-HEX",
            ),
            DashboardScheduleBlockDTO(
                id=uuid5(user_id, "block-thu-1"),
                day_of_week=4,
                day_label="Thứ Năm",
                start_time="09:00",
                end_time="10:30",
                title="Listening Part 4 Monologues Practice",
                category="Language",
                status="SCHEDULED",
                pomodoro_count=3,
                duration_minutes=90,
                roadmap_code="RD-IELTS-75",
            ),
            DashboardScheduleBlockDTO(
                id=uuid5(user_id, "block-fri-1"),
                day_of_week=5,
                day_label="Thứ Sáu",
                start_time="15:00",
                end_time="17:00",
                title="PostgreSQL pgvector & Semantic Search in Go",
                category="Engineering",
                status="SCHEDULED",
                pomodoro_count=4,
                duration_minutes=120,
                roadmap_code="RD-GO-HEX",
            ),
            DashboardScheduleBlockDTO(
                id=uuid5(user_id, "block-sat-1"),
                day_of_week=6,
                day_label="Thứ Bảy",
                start_time="08:30",
                end_time="11:30",
                title="Full IELTS Mock Test & Error Log Review",
                category="Assessment",
                status="SCHEDULED",
                pomodoro_count=6,
                duration_minutes=180,
                roadmap_code="RD-IELTS-75",
            ),
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
