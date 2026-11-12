from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from src.shared_kernel.domain.events import DomainEvent
from src.shared_kernel.domain.exceptions import DomainError

__all__ = [
    "DagCycleValidator",
    "DagDependencyEdge",
    "DagTaskNode",
    "DagTemporalViolation",
    "DagValidationError",
    "DagValidationResult",
    "ExecutionDashboardQueryPort",
    "ExecutionDayStudyDTO",
    "ExecutionKpiStatsDTO",
    "ExecutionScheduleSyncPort",
    "ExecutionTodayTaskDTO",
    "ExistingScheduledTaskDTO",
    "ExternalCalendarBusyUpdatedEvent",
    "ProposedDependencySyncItemDTO",
    "ProposedTaskSyncItemDTO",
    "ScheduleSyncResultDTO",
    "StudyExecutionQueryPort",
    "StudyExecutionStatsDTO",
    "StudySessionAbandonedEvent",
    "StudySessionCompletedEvent",
    "create_execution_dashboard_query_port",
    "create_execution_schedule_sync_port",
    "register_execution_dashboard_factory",
    "register_execution_sync_factory",
]


class DagValidationError(DomainError):
    """Raised when task dependencies violate DAG acyclic or temporal ordering invariants."""

    def __init__(
        self,
        message: str,
        code: str = "DEPENDENCY_CYCLE_DETECTED",
        cycle_path: list[UUID | str] | None = None,
    ) -> None:
        super().__init__(message=message, code=code)
        self.cycle_path = cycle_path or []


@dataclass(frozen=True, slots=True)
class DagTaskNode:
    """Pure domain representation of a task node for DAG and temporal validation."""

    task_id: UUID | str
    title: str = ""
    scheduled_date: date | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    task_index: int | None = None


@dataclass(frozen=True, slots=True)
class DagDependencyEdge:
    """Directed prerequisite edge: predecessor_id -> successor_id."""

    predecessor_id: UUID | str
    successor_id: UUID | str
    is_mandatory: bool = True


@dataclass(frozen=True, slots=True)
class DagTemporalViolation:
    """Details of a mandatory dependency where predecessor ends after successor starts."""

    predecessor_id: UUID | str
    successor_id: UUID | str
    predecessor_title: str
    successor_title: str
    predecessor_end_str: str
    successor_start_str: str
    message: str


@dataclass(frozen=True, slots=True)
class DagValidationResult:
    """Result of deterministic DAG validation."""

    is_valid: bool
    has_self_dependency: bool = False
    cycle_path: tuple[UUID | str, ...] = ()
    temporal_violations: tuple[DagTemporalViolation, ...] = ()
    error_messages: tuple[str, ...] = ()


class DagCycleValidator:
    """Pure Python deterministic DAG validator (UC-11 / UC-12 / ADR-009 Tier 2).

    Enforces:
    1. No self-dependency (predecessor_id != successor_id).
    2. No directed cycles (returns exact cycle path if found).
    3. Temporal ordering for mandatory dependencies (is_mandatory=True):
       predecessor's scheduled end must occur on or before successor's scheduled start.
    """

    @classmethod
    def validate(
        cls,
        tasks: Sequence[DagTaskNode],
        dependencies: Sequence[DagDependencyEdge],
    ) -> DagValidationResult:
        node_map: dict[UUID | str, DagTaskNode] = {t.task_id: t for t in tasks}
        error_messages: list[str] = []

        # 1. Check self-dependencies
        for edge in dependencies:
            if edge.predecessor_id == edge.successor_id:
                msg = f"Phát hiện phụ thuộc tự thân (self-dependency) tại nhiệm vụ '{edge.predecessor_id}'."
                return DagValidationResult(
                    is_valid=False,
                    has_self_dependency=True,
                    cycle_path=(edge.predecessor_id, edge.successor_id),
                    error_messages=(msg,),
                )

        # Build adjacency list preserving deterministic insertion order
        adj: dict[UUID | str, list[UUID | str]] = {t.task_id: [] for t in tasks}
        for edge in dependencies:
            adj.setdefault(edge.predecessor_id, [])
            adj.setdefault(edge.successor_id, [])
            if edge.successor_id not in adj[edge.predecessor_id]:
                adj[edge.predecessor_id].append(edge.successor_id)

        # 2. Cycle detection via 3-color DFS to extract exact cycle path
        state: dict[UUID | str, int] = {node_id: 0 for node_id in adj}
        stack: list[UUID | str] = []
        stack_index: dict[UUID | str, int] = {}

        def dfs(u: UUID | str) -> list[UUID | str] | None:
            state[u] = 1
            stack_index[u] = len(stack)
            stack.append(u)

            for v in adj.get(u, []):
                if state.get(v, 0) == 0:
                    cycle = dfs(v)
                    if cycle is not None:
                        return cycle
                elif state.get(v, 0) == 1:
                    start_idx = stack_index[v]
                    return [*stack[start_idx:], v]

            stack.pop()
            stack_index.pop(u, None)
            state[u] = 2
            return None

        for node_id in list(adj.keys()):
            if state[node_id] == 0:
                found_cycle = dfs(node_id)
                if found_cycle is not None:
                    readable = " -> ".join(
                        node_map[nid].title if nid in node_map and node_map[nid].title else str(nid)
                        for nid in found_cycle
                    )
                    msg = f"Phát hiện chu trình phụ thuộc (DAG cycle): {readable}."
                    return DagValidationResult(
                        is_valid=False,
                        has_self_dependency=False,
                        cycle_path=tuple(found_cycle),
                        error_messages=(msg,),
                    )

        # 3. Temporal ordering for mandatory dependencies
        temporal_violations: list[DagTemporalViolation] = []
        for edge in dependencies:
            if not edge.is_mandatory:
                continue
            pred = node_map.get(edge.predecessor_id)
            succ = node_map.get(edge.successor_id)
            if pred is None or succ is None:
                continue

            if pred.scheduled_end is not None and succ.scheduled_start is not None:
                if pred.scheduled_end > succ.scheduled_start:
                    pred_end_str = pred.scheduled_end.isoformat()
                    succ_start_str = succ.scheduled_start.isoformat()
                    pred_label = pred.title or str(pred.task_id)
                    succ_label = succ.title or str(succ.task_id)
                    msg = (
                        f"Vi phạm thứ tự thời gian bắt buộc: Nhiệm vụ tiền đề '{pred_label}' kết thúc lúc "
                        f"{pred_end_str} sau khi nhiệm vụ kế tiếp '{succ_label}' bắt đầu ({succ_start_str})."
                    )
                    temporal_violations.append(
                        DagTemporalViolation(
                            predecessor_id=edge.predecessor_id,
                            successor_id=edge.successor_id,
                            predecessor_title=pred_label,
                            successor_title=succ_label,
                            predecessor_end_str=pred_end_str,
                            successor_start_str=succ_start_str,
                            message=msg,
                        )
                    )
                    error_messages.append(msg)
                    continue

            if pred.scheduled_date is not None and succ.scheduled_date is not None:
                if pred.scheduled_date > succ.scheduled_date:
                    pred_end_str = pred.scheduled_date.isoformat()
                    succ_start_str = succ.scheduled_date.isoformat()
                    pred_label = pred.title or str(pred.task_id)
                    succ_label = succ.title or str(succ.task_id)
                    msg = (
                        f"Vi phạm thứ tự ngày học bắt buộc: Nhiệm vụ tiền đề '{pred_label}' ({pred_end_str}) "
                        f"xếp sau ngày của nhiệm vụ kế tiếp '{succ_label}' ({succ_start_str})."
                    )
                    temporal_violations.append(
                        DagTemporalViolation(
                            predecessor_id=edge.predecessor_id,
                            successor_id=edge.successor_id,
                            predecessor_title=pred_label,
                            successor_title=succ_label,
                            predecessor_end_str=pred_end_str,
                            successor_start_str=succ_start_str,
                            message=msg,
                        )
                    )
                    error_messages.append(msg)

        if temporal_violations:
            return DagValidationResult(
                is_valid=False,
                has_self_dependency=False,
                cycle_path=(),
                temporal_violations=tuple(temporal_violations),
                error_messages=tuple(error_messages),
            )

        return DagValidationResult(is_valid=True)

    @classmethod
    def assert_valid(
        cls,
        tasks: Sequence[DagTaskNode],
        dependencies: Sequence[DagDependencyEdge],
    ) -> DagValidationResult:
        result = cls.validate(tasks, dependencies)
        if not result.is_valid:
            code = (
                "DEPENDENCY_CYCLE_DETECTED"
                if (result.has_self_dependency or bool(result.cycle_path))
                else "DEPENDENCY_TEMPORAL_ORDER_VIOLATION"
            )
            raise DagValidationError(
                message="; ".join(result.error_messages) or "Vi phạm đồ thị phụ thuộc DAG.",
                code=code,
                cycle_path=list(result.cycle_path),
            )
        return result


@dataclass(frozen=True, kw_only=True)
class StudySessionCompletedEvent(DomainEvent):
    """Published when a learner finishes a Pomodoro or Stopwatch study session (UC-14)."""

    user_id: UUID
    session_id: UUID
    actual_duration_seconds: int


@dataclass(frozen=True, kw_only=True)
class StudySessionAbandonedEvent(DomainEvent):
    """Published when a stale session is auto-recovered after 5 minutes without heartbeat (UC-15)."""

    user_id: UUID
    session_id: UUID
    recovered_duration_seconds: int


@dataclass(frozen=True, kw_only=True)
class ExternalCalendarBusyUpdatedEvent(DomainEvent):
    """Published when Google Calendar 2-way sync detects updated busy slots (UC-16)."""

    user_id: UUID


@dataclass(frozen=True)
class StudyExecutionStatsDTO:
    """Read-only execution statistics for Evaluation and SRL profile aggregation."""

    user_id: UUID
    completed_sessions_count: int
    total_focus_seconds: int


class StudyExecutionQueryPort(Protocol):
    """Cross-context read-only query port for StudySession metrics."""

    async def get_user_execution_stats(self, user_id: UUID) -> StudyExecutionStatsDTO: ...


@dataclass(frozen=True, slots=True)
class ExistingScheduledTaskDTO:
    """Read-only DTO representing an already-scheduled task from an active roadmap (OS-04 EDF)."""

    task_id: UUID
    roadmap_id: UUID
    milestone_id: UUID
    title: str
    estimated_minutes: int
    scheduled_date: date | None
    scheduled_start: datetime | None
    scheduled_end: datetime | None
    status: str
    roadmap_target_date: date | None = None


@dataclass(frozen=True, slots=True)
class ProposedTaskSyncItemDTO:
    """Task item from a verified ScheduleProposal to be synced into `tasks` on Apply (UC-08 / UC-12)."""

    task_id: UUID
    milestone_id: UUID
    title: str
    description: str | None = None
    estimated_minutes: int = 30
    scheduled_date: date | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProposedDependencySyncItemDTO:
    """Dependency edge from a verified ScheduleProposal to be synced into `task_dependencies`."""

    predecessor_id: UUID
    successor_id: UUID
    is_mandatory: bool = True


@dataclass(frozen=True, slots=True)
class ScheduleSyncResultDTO:
    """Summary returned after applying OS-03 Merge / Future Shift on `tasks` and `task_dependencies`."""

    roadmap_id: UUID
    official_schedule_id: UUID
    preserved_completed_tasks_count: int
    replaced_tasks_count: int
    inserted_tasks_count: int
    affected_tasks_count: int
    total_shifted_minutes: int
    total_active_sessions: int
    total_planned_minutes: int


class ExecutionScheduleSyncPort(Protocol):
    """Cross-context facade port exposed by Execution to Planning for EDF conflict checks & OS-03 sync."""

    async def get_tasks_for_roadmaps(
        self,
        roadmap_ids: Sequence[UUID],
        *,
        roadmap_target_dates: Mapping[UUID, date | None] | None = None,
    ) -> list[ExistingScheduledTaskDTO]: ...

    async def get_active_roadmaps_tasks(
        self,
        user_id: UUID,
        exclude_roadmap_id: UUID | None = None,
        *,
        active_roadmap_ids: Sequence[UUID] | None = None,
        roadmap_target_dates: Mapping[UUID, date | None] | None = None,
    ) -> list[ExistingScheduledTaskDTO]: ...

    async def sync_official_schedule_tasks(
        self,
        *,
        roadmap_id: UUID,
        official_schedule_id: UUID,
        proposed_tasks: Sequence[ProposedTaskSyncItemDTO],
        proposed_dependencies: Sequence[ProposedDependencySyncItemDTO],
        now: datetime,
        protected_task_ids: Sequence[UUID] = (),
    ) -> ScheduleSyncResultDTO: ...


_execution_sync_factory: object = None


def register_execution_sync_factory(factory: object) -> None:
    global _execution_sync_factory
    _execution_sync_factory = factory


def create_execution_schedule_sync_port(session: object) -> ExecutionScheduleSyncPort:
    if _execution_sync_factory is None:
        import importlib

        importlib.import_module("src.execution.infrastructure.adapters")
    assert callable(_execution_sync_factory)
    res: ExecutionScheduleSyncPort = _execution_sync_factory(session)
    return res


@dataclass(frozen=True, slots=True)
class ExecutionTodayTaskDTO:
    id: UUID
    task_code: str
    title: str
    roadmap_title: str
    scheduled_time: str
    pomodoro_estimate: int
    duration_minutes: int
    status: str


@dataclass(frozen=True, slots=True)
class ExecutionKpiStatsDTO:
    monthly_study_seconds: int
    deep_work_seconds: int
    completed_pomodoro_count: int
    streak_days: int
    personal_best_streak: int
    streak_history_last_7_days: list[bool]
    adherence_rate_pct: float
    adherence_delta_pct: float
    overdue_tasks_count: int


@dataclass(frozen=True, slots=True)
class ExecutionDayStudyDTO:
    day_date: date
    day_label: str
    study_hours: float
    is_today: bool


class ExecutionDashboardQueryPort(Protocol):
    async def get_today_queue(self, user_id: UUID, today: date) -> list[ExecutionTodayTaskDTO]: ...

    async def get_7day_study_distribution(
        self, user_id: UUID, today: date
    ) -> list[ExecutionDayStudyDTO]: ...

    async def get_execution_kpis(self, user_id: UUID, today: date) -> ExecutionKpiStatsDTO: ...


_execution_dashboard_factory: object = None


def register_execution_dashboard_factory(factory: object) -> None:
    global _execution_dashboard_factory
    _execution_dashboard_factory = factory


def create_execution_dashboard_query_port(session: object) -> ExecutionDashboardQueryPort:
    global _execution_dashboard_factory
    if _execution_dashboard_factory is None:
        import importlib

        importlib.import_module("src.execution.infrastructure.adapters.execution_dashboard_adapter")
    assert callable(_execution_dashboard_factory)
    res: ExecutionDashboardQueryPort = _execution_dashboard_factory(session)
    return res
