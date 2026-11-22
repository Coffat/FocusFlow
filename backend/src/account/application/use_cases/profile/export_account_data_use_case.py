from datetime import UTC, datetime
from uuid import UUID

from src.account.application.dtos.export import (
    AccountDataExportDTO,
    ExportAnalyticsSummaryDTO,
    ExportAvailabilityDTO,
    ExportAvailabilitySlotDTO,
    ExportLearnerMemoryItemDTO,
    ExportLearnerProfileDTO,
    ExportRoadmapDTO,
    ExportStudySessionItemDTO,
    ExportTaskItemDTO,
    ExportUserDTO,
)
from src.account.application.ports.availability_repository_port import (
    AvailabilityRepositoryPort,
)
from src.account.application.ports.learner_memory_repository_port import (
    LearnerMemoryRepositoryPort,
)
from src.account.application.ports.learner_profile_repository_port import (
    LearnerProfileRepositoryPort,
)
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.execution.public_api import ExecutionDashboardQueryPort
from src.planning.public_api import PlanningExecutionBridgePort

_MAX_EXPORT_SESSIONS = 500
_MAX_EXPORT_TASKS = 1000


class ExportAccountDataUseCase:
    """Gather authenticated learner's personal data across bounded contexts for GDPR export.

    Strictly uses cross-context Query Ports (`planning.public_api`, `execution.public_api`),
    never exposes credentials/tokens/secrets, and never logs export payloads or PII.
    """

    def __init__(
        self,
        *,
        user_repo: UserRepositoryPort,
        learner_profile_repo: LearnerProfileRepositoryPort,
        learner_memory_repo: LearnerMemoryRepositoryPort,
        availability_repo: AvailabilityRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        execution_dashboard_port: ExecutionDashboardQueryPort,
    ) -> None:
        self._user_repo = user_repo
        self._learner_profile_repo = learner_profile_repo
        self._learner_memory_repo = learner_memory_repo
        self._availability_repo = availability_repo
        self._planning_bridge = planning_bridge
        self._execution_dashboard_port = execution_dashboard_port

    async def execute(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
    ) -> AccountDataExportDTO:
        exported_at = now or datetime.now(UTC)
        user = await self._user_repo.find_by_id(user_id)
        if user is None:
            raise ValueError("User not found")

        user_dto = ExportUserDTO(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            timezone=user.timezone,
            role=user.role,
            tier=user.tier,
            created_at=user.created_at,
        )

        # Learner SRL profile
        profile_rec = await self._learner_profile_repo.get_by_user_id(user_id)
        profile_dto = (
            ExportLearnerProfileDTO(
                optimal_focus_duration_mins=profile_rec.optimal_focus_duration_mins,
                peak_productivity_slots=list(profile_rec.peak_productivity_slots),
                estimation_bias_factor=float(profile_rec.estimation_bias_factor),
                weekly_completion_rate=float(profile_rec.weekly_completion_rate),
                total_completed_sessions=profile_rec.total_completed_sessions,
                is_cold_start=profile_rec.is_cold_start,
                last_aggregated_at=profile_rec.last_aggregated_at,
            )
            if profile_rec is not None
            else None
        )

        # Learner memory items
        memory_items = await self._learner_memory_repo.list_active(user_id)
        memory_dtos = [
            ExportLearnerMemoryItemDTO(
                id=item.id,
                memory_key=item.memory_key,
                value=dict(item.value),
                category=item.category.value,
                epistemic_level=item.epistemic_level.value,
                confidence=float(item.confidence),
                sample_size=item.sample_size,
                status=item.status.value,
                updated_at=item.updated_at,
            )
            for item in memory_items
        ]

        # Availability & slots
        avail = await self._availability_repo.get_by_user_id(user_id)
        avail_dto: ExportAvailabilityDTO | None = None
        if avail is not None:
            day_dtos = [
                ExportAvailabilitySlotDTO(
                    day_of_week=day_name,
                    enabled=day_sched.enabled,
                    quota_hours=day_sched.quota_hours,
                    preferred_period=day_sched.preferred_period.value,
                    min_session_minutes=day_sched.min_session_minutes,
                    time_slots=[
                        {
                            "start_time": slot.start_time.strftime("%H:%M"),
                            "end_time": slot.end_time.strftime("%H:%M"),
                            "end_day_offset": slot.end_day_offset,
                        }
                        for slot in day_sched.time_slots
                    ],
                )
                for day_name, day_sched in avail.weekly_schedule.days.items()
            ]
            avail_dto = ExportAvailabilityDTO(
                mode=avail.mode.value,
                calendar_integration_mode=avail.calendar_integration_mode.value,
                min_session_minutes=avail.min_session_minutes,
                total_weekly_hours=avail.weekly_schedule.calculate_total_weekly_hours(avail.mode),
                days=day_dtos,
            )

        # Roadmaps via Planning public_api
        roadmaps_ctx = await self._planning_bridge.get_user_roadmaps_context(user_id)
        roadmap_dtos = [
            ExportRoadmapDTO(
                roadmap_id=rm.roadmap_id,
                title=rm.title,
                status=rm.status,
                target_date=rm.target_date,
                weekly_reschedule_budget=rm.weekly_reschedule_budget,
                weekly_reschedule_used=rm.weekly_reschedule_used,
            )
            for rm in roadmaps_ctx
        ]

        # Analytics summary, bounded study sessions, bounded tasks via Execution public_api
        analytics = await self._execution_dashboard_port.get_analytics_summary(
            user_id,
            user_timezone=user.timezone,
            now=exported_at,
        )
        analytics_dto = ExportAnalyticsSummaryDTO(
            total_focused_hours=analytics.total_focused_hours,
            weekly_study_hours=analytics.weekly_study_hours,
            task_completion_rate=analytics.task_completion_rate,
            plan_adherence_rate=analytics.plan_adherence_rate,
            completed_tasks_count=analytics.completed_tasks_count,
            total_tasks_count=analytics.total_tasks_count,
            active_streak_days=analytics.active_streak_days,
            average_focus_score=analytics.average_focus_score,
        )

        (
            sessions_count,
            raw_sessions,
        ) = await self._execution_dashboard_port.get_user_export_sessions(
            user_id, limit=_MAX_EXPORT_SESSIONS
        )
        session_dtos = [
            ExportStudySessionItemDTO(
                id=s.id,
                roadmap_id=s.roadmap_id,
                session_mode=s.session_mode,
                status=s.status,
                planned_minutes=s.planned_minutes,
                actual_minutes=s.actual_minutes,
                started_at=s.started_at,
                ended_at=s.ended_at,
                created_at=s.created_at,
            )
            for s in raw_sessions
        ]

        tasks_count, raw_tasks = await self._execution_dashboard_port.get_user_export_tasks(
            user_id, limit=_MAX_EXPORT_TASKS
        )
        task_dtos = [
            ExportTaskItemDTO(
                id=t.id,
                roadmap_id=t.roadmap_id,
                milestone_id=t.milestone_id,
                title=t.title,
                description=t.description,
                estimated_minutes=t.estimated_minutes,
                scheduled_date=t.scheduled_date,
                status=t.status,
                completed_at=t.completed_at,
                created_at=t.created_at,
            )
            for t in raw_tasks
        ]

        return AccountDataExportDTO(
            schema_version="1.0",
            exported_at=exported_at,
            user=user_dto,
            learner_profile=profile_dto,
            learner_memory=memory_dtos,
            availability=avail_dto,
            roadmaps=roadmap_dtos,
            analytics_summary=analytics_dto,
            study_sessions_count=sessions_count,
            study_sessions=session_dtos,
            tasks_count=tasks_count,
            tasks=task_dtos,
        )
