import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import UUID

import structlog

from src.execution.public_api import (
    DagCycleValidator,
    DagDependencyEdge,
    DagTaskNode,
)
from src.planning.domain.exceptions.planning_exceptions import (
    ProposalValidationGateError,
    SoftOverflowConfirmationRequiredError,
)
from src.planning.domain.models.milestone import (
    AI_MILESTONE_MAX_COUNT,
    AI_MILESTONE_MIN_COUNT,
)
from src.planning.domain.services.spatio_temporal_engine import (
    SpatioTemporalRuleEngine,
)
from src.planning.domain.services.validation_types import (
    AI_BLOCK_MAX_MINUTES,
    AI_BLOCK_MIN_MINUTES,
    MANUAL_BLOCK_MAX_MINUTES,
    MANUAL_BLOCK_MIN_MINUTES,
    MAX_DAILY_PLANNED_MINUTES,
    AvailabilityConfigurationDTO,
    ConstraintViolationDTO,
    SoftOverflowWarningDTO,
    parse_iso_date,
    parse_iso_datetime,
)
from src.shared_kernel.application.llm_port import LLMProviderPort

logger = structlog.get_logger(__name__)

TIER3_JUDGE_TIMEOUT_SECONDS: float = 5.0
DEFAULT_MAX_RETRIES: int = 2


@dataclass(frozen=True, slots=True)
class ValidationGateResultDTO:
    """Comprehensive validation output from the 3-Tier Hybrid Validation Gate (ADR-009)."""

    is_valid: bool
    violations: tuple[ConstraintViolationDTO, ...] = ()
    soft_overflow_warnings: tuple[SoftOverflowWarningDTO, ...] = ()
    advisory_warnings: tuple[str, ...] = ()
    judge_skipped: bool = False
    pedagogical_score: float | None = None
    attempts_used: int = 1
    retry_history: tuple[dict[str, Any], ...] = ()
    validated_proposal_data: dict[str, Any] = field(default_factory=dict)
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0

    @property
    def has_soft_overflow(self) -> bool:
        return len(self.soft_overflow_warnings) > 0


class ProposalValidationGateOrchestrator:
    """3-Tier Hybrid Validation Gate & Self-Correction Retry Loop Orchestrator (UC-12 / ADR-009).

    - Tier 1 (Syntactic & Bound Gate):
      * AI-generated blocks: [30, 120] minutes (SRS v1.2 Spec Conflict #3 resolution).
      * Manual / Apply blocks: [15, 240] minutes.
      * AI milestone count: 3..7 with contiguous sequence_order 1..N.
      * Daily planned ceiling <= 720 minutes.
      * Every task references a valid milestone_id belonging to the roadmap.
    - Tier 2 (Deterministic Spatio-Temporal, Cross-Roadmap EDF & DAG Gate):
      * Mode A (QUOTA) daily ceiling + Cross-Roadmap EDF quota check.
      * Mode B (FIXED_SLOTS) slot fit + cross-midnight support + Soft Overflow <= 30m warning
        on last task of day vs > 30m hard error + Cross-Roadmap EDF slot overlap check.
      * DAG check via `DagCycleValidator` (no self-dependency, no cycle, mandatory temporal ordering).
    - Tier 3 (Pedagogical LLM-as-a-Judge Gate):
      * Strict timeout <= 5.0s (`asyncio.wait_for`), Fail-Open (`judge_skipped=True`) on timeout or error.
    - Self-Correction Retry Loop:
      * Up to `max_retries = 2` (3 total attempts) within a single quota reservation.
    """

    def __init__(
        self,
        llm_provider: LLMProviderPort | None = None,
        *,
        enable_tier3_judge: bool = False,
        tier3_timeout_seconds: float = TIER3_JUDGE_TIMEOUT_SECONDS,
    ) -> None:
        self._llm = llm_provider
        self._enable_tier3_judge = enable_tier3_judge
        self._tier3_timeout_seconds = min(tier3_timeout_seconds, TIER3_JUDGE_TIMEOUT_SECONDS)

    @staticmethod
    def validate_ai_milestones_tier1(
        milestones_data: Sequence[dict[str, Any]],
    ) -> list[ConstraintViolationDTO]:
        """Validate Tier 1 bounds for AI-generated Level-1 Milestones (3..7 count, 1..N sequence)."""
        violations: list[ConstraintViolationDTO] = []
        count = len(milestones_data)
        if not (AI_MILESTONE_MIN_COUNT <= count <= AI_MILESTONE_MAX_COUNT):
            violations.append(
                ConstraintViolationDTO(
                    task_index=None,
                    field="milestones",
                    rule_code="AI_MILESTONE_COUNT_OUT_OF_RANGE",
                    expected_bound=f"{AI_MILESTONE_MIN_COUNT}..{AI_MILESTONE_MAX_COUNT} milestones",
                    actual_value=f"{count} milestones",
                    suggested_fix=(
                        f"Sinh đúng từ {AI_MILESTONE_MIN_COUNT} đến {AI_MILESTONE_MAX_COUNT} cột mốc."
                    ),
                )
            )
            return violations

        orders: list[int] = []
        for idx, item in enumerate(milestones_data):
            seq = int(item.get("sequence_order", 0) or 0)
            title = str(item.get("title", "")).strip()
            orders.append(seq)
            if not title:
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="title",
                        rule_code="EMPTY_MILESTONE_TITLE",
                        expected_bound="Non-empty string",
                        actual_value="''",
                        suggested_fix="Cung cấp tiêu đề rõ ràng cho từng cột mốc.",
                    )
                )

        expected = list(range(1, count + 1))
        if sorted(orders) != expected:
            violations.append(
                ConstraintViolationDTO(
                    task_index=None,
                    field="sequence_order",
                    rule_code="INVALID_MILESTONE_SEQUENCE_ORDER",
                    expected_bound=f"Sequential 1..{count}",
                    actual_value=str(orders),
                    suggested_fix=f"Đánh số sequence_order liên tục từ 1 đến {count}.",
                )
            )

        return violations

    @classmethod
    def run_tier1_gate(
        cls,
        proposal_data: dict[str, Any],
        *,
        valid_milestone_ids: set[UUID | str] | None = None,
        is_ai_generated: bool = True,
    ) -> list[ConstraintViolationDTO]:
        """Execute Tier 1 Syntactic & Bound checks on a ScheduleProposal payload."""
        violations: list[ConstraintViolationDTO] = []

        if "milestones" in proposal_data and isinstance(proposal_data["milestones"], list):
            if is_ai_generated and len(proposal_data["milestones"]) > 0:
                violations.extend(cls.validate_ai_milestones_tier1(proposal_data["milestones"]))

        raw_tasks = proposal_data.get("tasks")
        if not isinstance(raw_tasks, list) or len(raw_tasks) == 0:
            violations.append(
                ConstraintViolationDTO(
                    task_index=None,
                    field="tasks",
                    rule_code="EMPTY_PROPOSAL_TASKS",
                    expected_bound="At least 1 study task",
                    actual_value="0 tasks",
                    suggested_fix="Cung cấp danh sách ít nhất 1 nhiệm vụ học tập trong trường 'tasks'.",
                )
            )
            return violations

        min_bound = AI_BLOCK_MIN_MINUTES if is_ai_generated else MANUAL_BLOCK_MIN_MINUTES
        max_bound = AI_BLOCK_MAX_MINUTES if is_ai_generated else MANUAL_BLOCK_MAX_MINUTES
        duration_rule_code = (
            "AI_TASK_DURATION_OUT_OF_BOUNDS"
            if is_ai_generated
            else "MANUAL_TASK_DURATION_OUT_OF_BOUNDS"
        )

        normalized_valid_mids: set[str] | None = (
            {str(mid) for mid in valid_milestone_ids} if valid_milestone_ids is not None else None
        )

        minutes_by_date: dict[date, list[tuple[int, int]]] = {}

        for idx, task in enumerate(raw_tasks):
            if not isinstance(task, dict):
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="tasks",
                        rule_code="INVALID_TASK_OBJECT",
                        expected_bound="JSON object",
                        actual_value=type(task).__name__,
                        suggested_fix="Mỗi phần tử trong 'tasks' phải là một đối tượng JSON.",
                    )
                )
                continue

            title = str(task.get("title", "")).strip()
            if not title:
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="title",
                        rule_code="EMPTY_TASK_TITLE",
                        expected_bound="Non-empty title",
                        actual_value="''",
                        suggested_fix=f"Đặt tiêu đề rõ ràng cho nhiệm vụ #{idx}.",
                    )
                )

            est_raw = task.get("estimated_minutes")
            try:
                est_mins = int(est_raw)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                est_mins = -1

            if not (min_bound <= est_mins <= max_bound):
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="estimated_minutes",
                        rule_code=duration_rule_code,
                        expected_bound=f"[{min_bound}, {max_bound}] phút",
                        actual_value=f"{est_mins} phút",
                        suggested_fix=(
                            f"Điều chỉnh thời lượng nhiệm vụ #{idx} ('{title}') nằm trong khoảng "
                            f"[{min_bound}, {max_bound}] phút."
                        ),
                    )
                )

            milestone_id = task.get("milestone_id")
            if normalized_valid_mids is not None:
                if milestone_id is None or str(milestone_id) not in normalized_valid_mids:
                    violations.append(
                        ConstraintViolationDTO(
                            task_index=idx,
                            field="milestone_id",
                            rule_code="INVALID_MILESTONE_REFERENCE",
                            expected_bound=f"Một trong các milestone_id hợp lệ của lộ trình: {sorted(normalized_valid_mids)}",
                            actual_value=str(milestone_id),
                            suggested_fix="Gán đúng milestone_id thuộc danh sách cột mốc đã phê duyệt của lộ trình.",
                        )
                    )

            sched_date = parse_iso_date(task.get("scheduled_date"))
            if sched_date is None:
                violations.append(
                    ConstraintViolationDTO(
                        task_index=idx,
                        field="scheduled_date",
                        rule_code="INVALID_SCHEDULED_DATE",
                        expected_bound="YYYY-MM-DD",
                        actual_value=str(task.get("scheduled_date")),
                        suggested_fix="Cung cấp ngày học hợp lệ theo định dạng YYYY-MM-DD.",
                    )
                )
            elif est_mins > 0:
                minutes_by_date.setdefault(sched_date, []).append((idx, est_mins))

        for sched_date, day_entries in minutes_by_date.items():
            daily_total = sum(m for _, m in day_entries)
            if daily_total > MAX_DAILY_PLANNED_MINUTES:
                last_idx = day_entries[-1][0]
                violations.append(
                    ConstraintViolationDTO(
                        task_index=last_idx,
                        field="estimated_minutes",
                        rule_code="DAILY_MAX_720M_EXCEEDED",
                        expected_bound=f"<= {MAX_DAILY_PLANNED_MINUTES} phút/ngày",
                        actual_value=f"{daily_total} phút vào ngày {sched_date.isoformat()}",
                        suggested_fix=(
                            f"Tổng thời lượng trong ngày {sched_date.isoformat()} vượt trần tuyệt đối "
                            f"{MAX_DAILY_PLANNED_MINUTES} phút. Hãy phân bổ bớt sang các ngày khác."
                        ),
                    )
                )

        return violations

    @classmethod
    def run_tier2_gate(
        cls,
        proposal_data: dict[str, Any],
        *,
        availability: AvailabilityConfigurationDTO,
        existing_tasks: Sequence[object] = (),
        current_roadmap_target_date: date | None = None,
    ) -> tuple[list[ConstraintViolationDTO], list[SoftOverflowWarningDTO]]:
        """Execute Tier 2 Deterministic Spatio-Temporal, Cross-Roadmap EDF & DAG checks."""
        violations: list[ConstraintViolationDTO] = []
        warnings: list[SoftOverflowWarningDTO] = []

        raw_tasks = proposal_data.get("tasks")
        if not isinstance(raw_tasks, list) or not raw_tasks:
            return violations, warnings

        mode_upper = (availability.mode or "MODE_A").strip().upper()
        is_mode_b = mode_upper in ("MODE_B", "FIXED_SLOTS", "SLOTS")

        if is_mode_b:
            b_violations, b_warnings = SpatioTemporalRuleEngine.validate_mode_b_slots(
                tasks=raw_tasks,
                availability=availability,
                existing_tasks=existing_tasks,
                current_roadmap_target_date=current_roadmap_target_date,
            )
            violations.extend(b_violations)
            warnings.extend(b_warnings)
        else:
            a_violations = SpatioTemporalRuleEngine.validate_mode_a_quota(
                tasks=raw_tasks,
                availability=availability,
                existing_tasks=existing_tasks,
                current_roadmap_target_date=current_roadmap_target_date,
            )
            violations.extend(a_violations)

        # Build DAG nodes & edges and run DagCycleValidator
        dag_nodes: list[DagTaskNode] = []
        index_by_id: dict[str, int] = {}

        for idx, t in enumerate(raw_tasks):
            if not isinstance(t, dict):
                continue
            tid = t.get("task_id") or t.get("id") or f"task_{idx}"
            tid_key = str(tid)
            index_by_id[tid_key] = idx
            dag_nodes.append(
                DagTaskNode(
                    task_id=tid_key,
                    title=str(t.get("title", f"Task #{idx}")),
                    scheduled_date=parse_iso_date(t.get("scheduled_date")),
                    scheduled_start=parse_iso_datetime(t.get("scheduled_start")),
                    scheduled_end=parse_iso_datetime(t.get("scheduled_end")),
                    task_index=idx,
                )
            )

        dag_edges: list[DagDependencyEdge] = []
        raw_deps = proposal_data.get("dependencies", [])
        if isinstance(raw_deps, list):
            for dep in raw_deps:
                if not isinstance(dep, dict):
                    continue
                pred_id = dep.get("predecessor_id")
                succ_id = dep.get("successor_id")
                if pred_id is None or succ_id is None:
                    continue
                is_mand = bool(dep.get("is_mandatory", True))
                dag_edges.append(
                    DagDependencyEdge(
                        predecessor_id=str(pred_id),
                        successor_id=str(succ_id),
                        is_mandatory=is_mand,
                    )
                )

        # Also support inline `prerequisite_ids` / `depends_on` on each task dict
        for idx, t in enumerate(raw_tasks):
            if not isinstance(t, dict):
                continue
            tid = str(t.get("task_id") or t.get("id") or f"task_{idx}")
            prereqs = t.get("prerequisite_ids") or t.get("depends_on") or []
            if isinstance(prereqs, list):
                for p in prereqs:
                    dag_edges.append(
                        DagDependencyEdge(
                            predecessor_id=str(p),
                            successor_id=tid,
                            is_mandatory=True,
                        )
                    )

        if dag_edges:
            dag_res = DagCycleValidator.validate(dag_nodes, dag_edges)
            if not dag_res.is_valid:
                if dag_res.has_self_dependency:
                    node_str = str(dag_res.cycle_path[0]) if dag_res.cycle_path else ""
                    violations.append(
                        ConstraintViolationDTO(
                            task_index=index_by_id.get(node_str),
                            field="dependencies",
                            rule_code="DAG_SELF_DEPENDENCY",
                            expected_bound="predecessor_id != successor_id",
                            actual_value=f"{node_str} -> {node_str}",
                            suggested_fix=f"Loại bỏ cạnh phụ thuộc tự thân tại nhiệm vụ '{node_str}'.",
                        )
                    )
                elif dag_res.cycle_path:
                    cycle_str = " -> ".join(str(x) for x in dag_res.cycle_path)
                    first_node = str(dag_res.cycle_path[0])
                    violations.append(
                        ConstraintViolationDTO(
                            task_index=index_by_id.get(first_node),
                            field="dependencies",
                            rule_code="DEPENDENCY_CYCLE_DETECTED",
                            expected_bound="Acyclic directed graph (DAG)",
                            actual_value=cycle_str,
                            suggested_fix=f"Phá vỡ chu trình phụ thuộc bằng cách gỡ ít nhất một cạnh trong: {cycle_str}.",
                        )
                    )
                for tv in dag_res.temporal_violations:
                    succ_idx = index_by_id.get(str(tv.successor_id))
                    violations.append(
                        ConstraintViolationDTO(
                            task_index=succ_idx,
                            field="scheduled_start",
                            rule_code="DEPENDENCY_TEMPORAL_ORDER_VIOLATION",
                            expected_bound=(
                                f"Bắt đầu sau khi nhiệm vụ tiền đề '{tv.predecessor_title}' kết thúc "
                                f"({tv.predecessor_end_str})"
                            ),
                            actual_value=f"'{tv.successor_title}' bắt đầu lúc {tv.successor_start_str}",
                            suggested_fix=(
                                f"Dời lịch nhiệm vụ '{tv.successor_title}' sang sau mốc {tv.predecessor_end_str}."
                            ),
                        )
                    )

        return violations, warnings

    async def run_tier3_pedagogical_judge(
        self,
        proposal_data: dict[str, Any],
        *,
        goal_title: str = "",
    ) -> tuple[bool, float | None, list[str]]:
        """Execute Tier 3 Pedagogical LLM-as-a-Judge with strict <= 5.0s timeout & Fail-Open (ADR-009).

        Returns: `(judge_skipped, pedagogical_score, advisory_warnings)`
        """
        if not self._enable_tier3_judge or self._llm is None:
            return False, None, []

        judge_system_prompt = (
            "Bạn là chuyên gia đánh giá sư phạm theo mô hình Zimmerman SRL. "
            "Hãy đánh giá ngắn gọn tính hợp lý sư phạm của lịch học đề xuất (JSON: "
            '{"score": 0.0..1.0, "advisory_warnings": ["..."]}).'
        )
        judge_user_prompt = (
            f"Mục tiêu: {goal_title}\nSố nhiệm vụ: {len(proposal_data.get('tasks', []))}"
        )

        try:
            coro = self._llm.generate_structured(
                prompt=judge_user_prompt,
                system_prompt=judge_system_prompt,
                response_schema={
                    "type": "object",
                    "properties": {
                        "score": {"type": "number"},
                        "advisory_warnings": {"type": "array", "items": {"type": "string"}},
                    },
                },
                temperature=0.1,
            )
            judge_dict, _, _ = await asyncio.wait_for(
                coro,
                timeout=self._tier3_timeout_seconds,
            )
            score_raw = judge_dict.get("score")
            score = float(score_raw) if isinstance(score_raw, (int, float)) else 0.85
            adv_raw = judge_dict.get("advisory_warnings", [])
            advisories = (
                [str(w) for w in adv_raw if str(w).strip()] if isinstance(adv_raw, list) else []
            )
            return False, score, advisories
        except TimeoutError:
            logger.warning(
                "tier3_pedagogical_judge_timeout_fail_open",
                timeout_seconds=self._tier3_timeout_seconds,
            )
            return (
                True,
                None,
                [
                    "Tier 3 Pedagogical Judge quá thời gian chờ (5s) — đã bỏ qua theo cơ chế Fail-Open (ADR-009)."
                ],
            )
        except Exception as exc:
            logger.warning(
                "tier3_pedagogical_judge_error_fail_open",
                error=str(exc),
            )
            return (
                True,
                None,
                [
                    "Tier 3 Pedagogical Judge tạm thời không phản hồi — đã bỏ qua theo cơ chế Fail-Open (ADR-009)."
                ],
            )

    async def validate_proposal(
        self,
        proposal_data: dict[str, Any],
        *,
        availability: AvailabilityConfigurationDTO,
        valid_milestone_ids: set[UUID | str] | None = None,
        existing_tasks: Sequence[object] = (),
        current_roadmap_target_date: date | None = None,
        is_ai_generated: bool = True,
        require_soft_overflow_confirmation: bool = False,
        confirm_soft_overflow: bool = False,
        goal_title: str = "",
    ) -> ValidationGateResultDTO:
        """Run all 3 Tiers on a single proposal payload."""
        tier1_violations = self.run_tier1_gate(
            proposal_data,
            valid_milestone_ids=valid_milestone_ids,
            is_ai_generated=is_ai_generated,
        )
        tier2_violations, soft_warnings = self.run_tier2_gate(
            proposal_data,
            availability=availability,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=current_roadmap_target_date,
        )

        all_violations = [*tier1_violations, *tier2_violations]
        if all_violations:
            return ValidationGateResultDTO(
                is_valid=False,
                violations=tuple(all_violations),
                soft_overflow_warnings=tuple(soft_warnings),
                validated_proposal_data=proposal_data,
            )

        if require_soft_overflow_confirmation and soft_warnings and not confirm_soft_overflow:
            total_overflow = sum(w.overflow_minutes for w in soft_warnings)
            raise SoftOverflowConfirmationRequiredError(overflow_minutes=total_overflow)

        judge_skipped, score, advisories = await self.run_tier3_pedagogical_judge(
            proposal_data,
            goal_title=goal_title,
        )

        enriched_data = dict(proposal_data)
        enriched_data["soft_overflow_warnings"] = [w.to_dict() for w in soft_warnings]
        if advisories:
            enriched_data["advisory_warnings"] = advisories
        if judge_skipped:
            enriched_data["judge_skipped"] = True

        return ValidationGateResultDTO(
            is_valid=True,
            violations=(),
            soft_overflow_warnings=tuple(soft_warnings),
            advisory_warnings=tuple(advisories),
            judge_skipped=judge_skipped,
            pedagogical_score=score,
            validated_proposal_data=enriched_data,
        )

    @staticmethod
    def build_self_correction_prompt(
        original_user_prompt: str,
        violations: Sequence[ConstraintViolationDTO],
        attempt_number: int,
    ) -> str:
        """Format structured ConstraintViolationDTO list into a deterministic correction prompt."""
        lines = [
            original_user_prompt,
            "",
            f"[SELF-CORRECTION RETRY ATTEMPT #{attempt_number}]",
            "Đề xuất lịch học vừa sinh vi phạm các ràng buộc tất định sau đây. Hãy sửa chính xác từng lỗi:",
        ]
        for idx, v in enumerate(violations, start=1):
            task_ref = f"task_index={v.task_index}" if v.task_index is not None else "toàn cục"
            lines.append(
                f"{idx}. [{v.rule_code}] ({task_ref}, trường '{v.field}'): "
                f"Giá trị hiện tại = {v.actual_value} | Yêu cầu = {v.expected_bound} | "
                f"Cách sửa = {v.suggested_fix}"
            )
        lines.append("Chỉ trả về JSON hợp lệ đã khắc phục triệt để tất cả các vi phạm trên.")
        return "\n".join(lines)

    async def generate_and_validate_proposal_with_retry(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | type[Any] | None,
        availability: AvailabilityConfigurationDTO,
        valid_milestone_ids: set[UUID | str] | None = None,
        existing_tasks: Sequence[object] = (),
        current_roadmap_target_date: date | None = None,
        goal_title: str = "",
        max_retries: int = DEFAULT_MAX_RETRIES,
        on_retry_callback: Callable[[int, Sequence[ConstraintViolationDTO]], Any] | None = None,
    ) -> ValidationGateResultDTO:
        """Invoke LLMProviderPort and run the 3-Tier Validation Gate with up to `max_retries` (2) self-correction loops."""
        if self._llm is None:
            raise ValueError(
                "LLMProviderPort is required for generate_and_validate_proposal_with_retry."
            )

        current_prompt = user_prompt
        total_prompt_tokens = 0
        total_completion_tokens = 0
        retry_history: list[dict[str, Any]] = []
        last_violations: list[ConstraintViolationDTO] = []

        max_attempts = max(1, int(max_retries) + 1)

        for attempt in range(1, max_attempts + 1):
            raw_proposal, p_tokens, c_tokens = await self._llm.generate_structured(
                prompt=current_prompt,
                system_prompt=system_prompt,
                response_schema=response_schema,
                user_prompt=current_prompt,
                temperature=0.2,
            )
            total_prompt_tokens += int(p_tokens or 0)
            total_completion_tokens += int(c_tokens or 0)

            gate_result = await self.validate_proposal(
                raw_proposal,
                availability=availability,
                valid_milestone_ids=valid_milestone_ids,
                existing_tasks=existing_tasks,
                current_roadmap_target_date=current_roadmap_target_date,
                is_ai_generated=True,
                goal_title=goal_title,
            )

            if gate_result.is_valid:
                return ValidationGateResultDTO(
                    is_valid=True,
                    violations=(),
                    soft_overflow_warnings=gate_result.soft_overflow_warnings,
                    advisory_warnings=gate_result.advisory_warnings,
                    judge_skipped=gate_result.judge_skipped,
                    pedagogical_score=gate_result.pedagogical_score,
                    attempts_used=attempt,
                    retry_history=tuple(retry_history),
                    validated_proposal_data=gate_result.validated_proposal_data,
                    total_prompt_tokens=total_prompt_tokens,
                    total_completion_tokens=total_completion_tokens,
                )

            last_violations = list(gate_result.violations)
            retry_record = {
                "attempt": attempt,
                "violations": [v.to_dict() for v in last_violations],
            }
            retry_history.append(retry_record)

            if attempt < max_attempts:
                if on_retry_callback is not None:
                    maybe_coro = on_retry_callback(attempt, last_violations)
                    if asyncio.iscoroutine(maybe_coro):
                        await maybe_coro
                current_prompt = self.build_self_correction_prompt(
                    user_prompt,
                    last_violations,
                    attempt_number=attempt,
                )

        raise ProposalValidationGateError(
            message=(
                f"Đề xuất lịch học của AI vẫn vi phạm ràng buộc sau {max_attempts} lần thử "
                f"(tối đa {max_retries} vòng tự sửa lỗi)."
            ),
            code="AI_SCHEMA_VALIDATION_ERROR",
            violations=[v.to_dict() for v in last_violations],
        )
