import json
import math
from collections.abc import Sequence
from datetime import UTC, date, datetime, time
from typing import Any

from src.planning.application.dtos.planning_dtos import (
    ClarificationContextPayload,
    parse_clarification_context,
)
from src.planning.application.ports.knowledge_base_port import KnowledgeBasePort
from src.planning.application.services.clarification_gap_analysis import (
    GapStatus,
    GoalFactProvenance,
    InformationGapAnalyzer,
)
from src.planning.domain.models.goal import Goal
from src.planning.domain.models.knowledge_concept import (
    ConceptPrerequisiteGraph,
    LearningConcept,
)
from src.planning.domain.models.milestone import Milestone
from src.planning.domain.models.roadmap import Roadmap
from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
from src.planning.domain.services.validation_types import (
    AI_BLOCK_MAX_MINUTES,
    AI_BLOCK_MIN_MINUTES,
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
)
from src.shared_kernel.application.harness.context_engine import (
    AssembledContext,
    ContextEngine,
)
from src.shared_kernel.application.harness.models import HarnessContext
from src.shared_kernel.application.harness.untrusted_context import (
    UntrustedBlockKind,
    format_untrusted_block,
    sanitize_untrusted_text,
    sanitize_untrusted_value,
    wrap_untrusted_knowledge_context,
)


def _coerce_availability_dto(availability: Any) -> AvailabilityConfigurationDTO:
    if isinstance(availability, AvailabilityConfigurationDTO):
        return availability
    if availability is None:
        return AvailabilityConfigurationDTO()

    if isinstance(availability, dict):
        mode = str(availability.get("mode", "MODE_A"))
        raw_default_quota = availability.get("default_daily_quota_minutes")
        if raw_default_quota is None:
            raw_default_quota = availability.get("daily_cap_minutes", 120)
        raw_daily_quotas = dict(availability.get("daily_quota_minutes", {}) or {})
        raw_disabled = availability.get("disabled_weekdays", ()) or ()
        raw_slots = availability.get("availability_slots", ()) or ()
        timezone = str(availability.get("timezone", "UTC") or "UTC")
    else:
        mode = str(getattr(availability, "mode", "MODE_A"))
        raw_default_quota = getattr(availability, "default_daily_quota_minutes", None)
        if raw_default_quota is None:
            raw_default_quota = getattr(availability, "daily_cap_minutes", 120)
        raw_daily_quotas = dict(getattr(availability, "daily_quota_minutes", {}) or {})
        raw_disabled = getattr(availability, "disabled_weekdays", ()) or ()
        raw_slots = getattr(availability, "availability_slots", ()) or ()
        timezone = str(getattr(availability, "timezone", "UTC") or "UTC")

    slots: list[AvailabilitySlotDTO] = []
    for slot in raw_slots:
        if isinstance(slot, AvailabilitySlotDTO):
            slots.append(slot)
        elif isinstance(slot, dict):
            slots.append(
                AvailabilitySlotDTO(
                    day_of_week=slot.get("day_of_week", "monday"),
                    start_time=slot.get("start_time", "19:00"),
                    end_time=slot.get("end_time", "21:00"),
                    end_day_offset=int(slot.get("end_day_offset", 0) or 0),
                    is_active=bool(slot.get("is_active", True)),
                )
            )
        else:
            slots.append(
                AvailabilitySlotDTO(
                    day_of_week=getattr(slot, "day_of_week", "monday"),
                    start_time=getattr(slot, "start_time", "19:00"),
                    end_time=getattr(slot, "end_time", "21:00"),
                    end_day_offset=int(getattr(slot, "end_day_offset", 0) or 0),
                    is_active=bool(getattr(slot, "is_active", True)),
                )
            )

    return AvailabilityConfigurationDTO(
        mode=mode,
        daily_quota_minutes={str(k).lower(): int(v) for k, v in raw_daily_quotas.items()},
        default_daily_quota_minutes=int(
            raw_default_quota if raw_default_quota is not None else 120
        ),
        availability_slots=tuple(slots),
        disabled_weekdays=frozenset(str(d).lower() for d in raw_disabled),
        timezone=timezone,
    )


def _serialize_availability_slot(slot: Any) -> dict[str, Any]:
    if isinstance(slot, dict):
        return {
            "day_of_week": slot.get("day_of_week"),
            "start_time": (
                slot["start_time"].strftime("%H:%M")
                if isinstance(slot.get("start_time"), time)
                else slot.get("start_time")
            ),
            "end_time": (
                slot["end_time"].strftime("%H:%M")
                if isinstance(slot.get("end_time"), time)
                else slot.get("end_time")
            ),
            "end_day_offset": int(slot.get("end_day_offset", 0) or 0),
            "is_active": bool(slot.get("is_active", True)),
        }
    raw_start = getattr(slot, "start_time", None)
    raw_end = getattr(slot, "end_time", None)
    return {
        "day_of_week": getattr(slot, "day_of_week", None),
        "start_time": raw_start.strftime("%H:%M") if isinstance(raw_start, time) else raw_start,
        "end_time": raw_end.strftime("%H:%M") if isinstance(raw_end, time) else raw_end,
        "end_day_offset": int(getattr(slot, "end_day_offset", 0) or 0),
        "is_active": bool(getattr(slot, "is_active", True)),
    }


class RoadmapContextBuilder:
    """Builds structured 4-layer context blocks for the AI Learning Roadmap Generation Engine.

    Strictly separates:
    1. [USER_PROVIDED_FACTS]
    2. [SYSTEM_DERIVED_FACTS]
    3. [KNOWLEDGE_BASE_EVIDENCE]
    4. [AI_ASSUMPTIONS_AND_UNKNOWNS]
    """

    @staticmethod
    def extract_known_diagnostic_dimensions(goal: Goal) -> list[str]:
        """Compatibility view of dimensions proven KNOWN by the v2 gap analyzer."""
        parsed = parse_clarification_context(goal.clarification_context)
        gaps = InformationGapAnalyzer().analyze(
            goal=goal,
            provenance=GoalFactProvenance.from_mapping(parsed.input_provenance),
            weekly_commitment_hours=parsed.weekly_commitment_hours,
            availability_weekly_minutes=None,
        )
        return [gap.dimension for gap in gaps if gap.status is GapStatus.KNOWN]

    @classmethod
    def _format_clarification_payload(
        cls,
        raw_clarification: str | None,
        prior_level: str,
        *,
        include_information_gaps: bool = True,
    ) -> tuple[list[str], list[str]]:
        """Return (user_facts_lines, assumptions_lines) from goal.clarification_context."""
        user_lines: list[str] = []
        assumption_lines: list[str] = []

        parsed: ClarificationContextPayload = parse_clarification_context(
            raw_clarification,
            prior_knowledge_level=prior_level,
        )
        assumption_lines.append(f"clarification_status: {parsed.status}")
        if parsed.answers:
            user_lines.append("clarification_answers:")
            for item in parsed.answers:
                q_id = sanitize_untrusted_text(str(item.get("question_id", "")).strip())
                q_txt = sanitize_untrusted_text(str(item.get("question_text", "")))
                ans_block = format_untrusted_block(
                    UntrustedBlockKind.LEARNER_ANSWER,
                    str(item.get("answer", "")),
                    attributes={"question_id": q_id or "q"},
                )
                user_lines.append(f"  - [{q_id}] {q_txt} => {ans_block}")
        elif parsed.synthesized_text and parsed.status == "ANSWERED":
            sanitized_block = format_untrusted_block(
                UntrustedBlockKind.CLARIFICATION_DATA,
                parsed.synthesized_text,
            )
            user_lines.append(f"clarification_notes: {sanitized_block}")

        if parsed.facts:
            user_lines.append("normalized_clarification_facts:")
            for fact in parsed.facts:
                safe_fact = sanitize_untrusted_value(fact)
                user_lines.append("  - " + json.dumps(safe_fact, ensure_ascii=False, default=str))

        if include_information_gaps and parsed.information_gaps:
            assumption_lines.append("information_gaps:")
            for gap in parsed.information_gaps:
                if str(gap.get("status", "")) != "KNOWN":
                    safe_gap = sanitize_untrusted_value(gap)
                    assumption_lines.append(
                        "  - " + json.dumps(safe_gap, ensure_ascii=False, default=str)
                    )

        if parsed.skipped_questions:
            safe_skipped = [sanitize_untrusted_text(str(q)) for q in parsed.skipped_questions]
            assumption_lines.append(f"skipped_questions: {', '.join(safe_skipped)}")

        if parsed.unresolved_assumptions:
            for assumption_item in parsed.unresolved_assumptions:
                assumption_lines.append(
                    f"unresolved_assumption: {sanitize_untrusted_text(assumption_item)}"
                )
        elif parsed.status in ("SKIPPED", "PARTIAL"):
            assumption_lines.append(
                f"unresolved_assumption: Người học ở trạng thái khảo sát {parsed.status}; ưu tiên lộ trình cốt lõi an toàn cho trình độ '{prior_level}'."
            )

        return user_lines, assumption_lines

    @classmethod
    def _format_kb_evidence(
        cls,
        kb_concepts: Sequence[LearningConcept] = (),
        kb_graphs: Sequence[ConceptPrerequisiteGraph] = (),
    ) -> list[str]:
        lines: list[str] = []
        seen_concepts: dict[str, LearningConcept] = {}
        for c in kb_concepts:
            seen_concepts[c.concept_id] = c
        for g in kb_graphs:
            for node in g.nodes:
                seen_concepts.setdefault(node.concept_id, node)

        if not seen_concepts and not kb_graphs:
            lines.append("verified_concepts_count: 0")
            lines.append(
                "note: Chưa có khái niệm thực nghiệm hoặc cần gọi tool search_learning_concepts / get_concept_prerequisite_graph."
            )
            return lines

        lines.append(f"verified_concepts_count: {len(seen_concepts)}")
        for c in seen_concepts.values():
            outcomes_str = "; ".join(sanitize_untrusted_text(o) for o in c.learning_outcomes[:2])
            lines.append(
                f"- concept_id={sanitize_untrusted_text(c.concept_id)} | "
                f"title={sanitize_untrusted_text(c.title)} | domain={sanitize_untrusted_text(c.domain)} | "
                f"level={sanitize_untrusted_text(c.difficulty_level)} | effort_min={c.estimated_effort_minutes} | "
                f"status={c.verification_status.value} | outcomes={outcomes_str}"
            )

        all_edges: list[str] = []
        unresolved: set[str] = set()
        for g in kb_graphs:
            for e in g.edges:
                all_edges.append(
                    f"  * {sanitize_untrusted_text(e.prerequisite_concept_id)} "
                    f"--({e.relation_type.value}, depth={e.depth})--> "
                    f"{sanitize_untrusted_text(e.source_concept_id)}: "
                    f"{sanitize_untrusted_text(e.rationale)}"
                )
            for u in g.unresolved_ids:
                unresolved.add(sanitize_untrusted_text(u))

        if all_edges:
            lines.append("verified_prerequisite_edges:")
            lines.extend(all_edges)
        if unresolved:
            lines.append(f"unresolved_concept_ids: {', '.join(sorted(unresolved))}")

        return lines

    @classmethod
    def build_clarification_context(
        cls,
        goal: Goal,
        learner_profile: Any | None = None,
        *,
        include_information_gaps: bool = True,
    ) -> str:
        safe_title = format_untrusted_block(UntrustedBlockKind.GOAL_TITLE, goal.title)
        safe_desc = format_untrusted_block(
            UntrustedBlockKind.GOAL_RAW_DESCRIPTION,
            goal.raw_description or "Chưa có mô tả chi tiết.",
        )
        known_dims = cls.extract_known_diagnostic_dimensions(goal)
        parsed = parse_clarification_context(goal.clarification_context)
        user_clar_lines, assumption_lines = cls._format_clarification_payload(
            goal.clarification_context,
            goal.prior_knowledge_level,
            include_information_gaps=include_information_gaps,
        )

        system_lines = [
            f"goal_id: {goal.id}",
            f"known_diagnostic_dimensions: {json.dumps(known_dims, ensure_ascii=False)}",
            f"input_provenance: {json.dumps(parsed.input_provenance, ensure_ascii=False)}",
            f"weekly_commitment_hours: {parsed.weekly_commitment_hours if parsed.weekly_commitment_hours is not None else 'UNSPECIFIED'}",
        ]
        if learner_profile is not None:
            opt_min = getattr(learner_profile, "opt_session_minutes", None)
            if opt_min is not None:
                system_lines.append(f"learner_opt_session_minutes: {opt_min}")

        sections = [
            "[USER_PROVIDED_FACTS]",
            safe_title,
            safe_desc,
            f"prior_knowledge_level: {goal.prior_knowledge_level}",
            f"target_date: {goal.target_date.isoformat() if goal.target_date else 'UNSPECIFIED'}",
            f"weekly_commitment_hours: {parsed.weekly_commitment_hours if parsed.weekly_commitment_hours is not None else 'UNSPECIFIED'}",
            *user_clar_lines,
            "",
            "[SYSTEM_DERIVED_FACTS]",
            *system_lines,
            "",
            "[KNOWLEDGE_BASE_EVIDENCE]",
            "stage_policy: GOAL_CLARIFICATION không gọi Knowledge Base tools.",
            "",
            "[AI_ASSUMPTIONS_AND_UNKNOWNS]",
            *assumption_lines,
            "instruction: Chỉ đặt câu hỏi về những thông tin CHƯA xuất hiện trong [USER_PROVIDED_FACTS].",
        ]
        return "\n".join(sections)

    @classmethod
    def build_milestone_planning_context(
        cls,
        goal: Goal,
        roadmap: Roadmap | None = None,
        learner_profile: Any | None = None,
        kb_concepts: Sequence[LearningConcept] = (),
        kb_graphs: Sequence[ConceptPrerequisiteGraph] = (),
    ) -> str:
        safe_title = format_untrusted_block(UntrustedBlockKind.GOAL_TITLE, goal.title)
        safe_desc = format_untrusted_block(
            UntrustedBlockKind.GOAL_RAW_DESCRIPTION,
            goal.raw_description or "Chưa có mô tả chi tiết.",
        )
        user_clar_lines, assumption_lines = cls._format_clarification_payload(
            goal.clarification_context, goal.prior_knowledge_level
        )

        sys_lines: list[str] = [f"goal_id: {goal.id}"]
        if roadmap is not None:
            sys_lines.append(f"roadmap_id: {roadmap.id}")
            sys_lines.append(
                f"roadmap_start_date: {roadmap.start_date.isoformat() if roadmap.start_date else 'UNSPECIFIED'}"
            )
            sys_lines.append(
                f"roadmap_target_date: {roadmap.target_date.isoformat() if roadmap.target_date else 'UNSPECIFIED'}"
            )
        if learner_profile is not None:
            opt_min = getattr(learner_profile, "opt_session_minutes", None)
            if opt_min is not None:
                sys_lines.append(f"opt_session_minutes: {opt_min}")

        kb_lines = cls._format_kb_evidence(kb_concepts=kb_concepts, kb_graphs=kb_graphs)

        sections = [
            "[USER_PROVIDED_FACTS]",
            safe_title,
            safe_desc,
            f"prior_knowledge_level: {goal.prior_knowledge_level}",
            f"target_date: {goal.target_date.isoformat() if goal.target_date else 'UNSPECIFIED'}",
            *user_clar_lines,
            "",
            "[SYSTEM_DERIVED_FACTS]",
            *sys_lines,
            "",
            "[KNOWLEDGE_BASE_EVIDENCE]",
            *kb_lines,
            "",
            "[AI_ASSUMPTIONS_AND_UNKNOWNS]",
            *assumption_lines,
            "instruction: Mọi khái niệm lấy từ [KNOWLEDGE_BASE_EVIDENCE] đặt vào required_concepts; các khái niệm ngoài KB bắt buộc đặt vào unverified_concepts, tuyệt đối không bịa mã khái niệm VERIFIED.",
        ]
        return "\n".join(sections)

    @staticmethod
    async def prefetch_milestone_kb_evidence(
        knowledge_base: KnowledgeBasePort | None,
        *,
        query_text: str,
        learner_level: str | None = None,
        domain: str | None = None,
        limit: int = 10,
        max_depth: int = 3,
    ) -> tuple[list[LearningConcept], list[ConceptPrerequisiteGraph]]:
        """Prefetch verified KB concepts and prerequisite DAG on the server before LLM call."""
        if knowledge_base is None:
            return [], []
        normalized_query = " ".join(query_text.split())[:200]
        if not normalized_query:
            return [], []
        concepts = await knowledge_base.search_concepts(
            query=normalized_query,
            domain=domain,
            learner_level=learner_level,
            limit=limit,
        )
        if not concepts and domain:
            concepts = await knowledge_base.search_concepts(
                query=normalized_query,
                domain=None,
                learner_level=learner_level,
                limit=limit,
            )
        graphs: list[ConceptPrerequisiteGraph] = []
        if concepts:
            graph = await knowledge_base.get_prerequisite_graph(
                concept_ids=[c.concept_id for c in concepts],
                max_depth=max_depth,
            )
            graphs.append(graph)
        return concepts, graphs

    @staticmethod
    def compute_schedule_budget(
        *,
        availability: Any,
        milestones: Sequence[Any],
        start_date: date,
        target_date: date | None,
        learner_profile: Any | None = None,
        existing_tasks: Sequence[Any] = (),
        daily_workload_cap_minutes: int | None = None,
        default_milestone_effort_minutes: int = 60,
    ) -> dict[str, Any]:
        """Compute deterministic schedule budget metrics for Task Decomposer context."""
        avail_dto = _coerce_availability_dto(availability)
        max_available_minutes_until_target_date = int(
            SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
                avail_dto,
                start_date=start_date,
                target_date=target_date,
                existing_tasks=existing_tasks,
                daily_workload_cap_minutes=daily_workload_cap_minutes,
            )
        )

        total_milestone_effort_minutes = 0
        for milestone in milestones:
            raw_effort = (
                milestone.get("estimated_effort_minutes")
                if isinstance(milestone, dict)
                else getattr(milestone, "estimated_effort_minutes", None)
            )
            effort = int(raw_effort) if raw_effort is not None else default_milestone_effort_minutes
            total_milestone_effort_minutes += max(0, effort)

        raw_opt = (
            learner_profile.get("opt_session_minutes")
            if isinstance(learner_profile, dict)
            else getattr(learner_profile, "opt_session_minutes", None)
        )
        opt_session_minutes = int(raw_opt) if raw_opt is not None else 45
        recommended_minutes_per_task = min(
            AI_BLOCK_MAX_MINUTES,
            max(AI_BLOCK_MIN_MINUTES, opt_session_minutes),
        )

        max_tasks = max(
            0,
            max_available_minutes_until_target_date // recommended_minutes_per_task,
        )
        effort_floor = (
            math.ceil(total_milestone_effort_minutes / AI_BLOCK_MAX_MINUTES)
            if total_milestone_effort_minutes > 0
            else 0
        )
        raw_min_tasks = max(len(milestones), effort_floor)
        min_tasks = min(raw_min_tasks, max_tasks)

        fits_milestone_effort = (
            total_milestone_effort_minutes <= max_available_minutes_until_target_date
        )
        capacity_fit_ratio = (
            1.0
            if total_milestone_effort_minutes <= 0
            else round(
                max_available_minutes_until_target_date / total_milestone_effort_minutes,
                4,
            )
        )

        return {
            "max_available_minutes_until_target_date": max_available_minutes_until_target_date,
            "total_milestone_effort_minutes": total_milestone_effort_minutes,
            "recommended_minutes_per_task": recommended_minutes_per_task,
            "recommended_task_count_range": {
                "min_tasks": min_tasks,
                "max_tasks": max_tasks,
            },
            "capacity_fit_ratio": capacity_fit_ratio,
            "fits_milestone_effort": fits_milestone_effort,
        }

    @classmethod
    def build_task_decomposition_context(
        cls,
        goal: Goal,
        roadmap: Roadmap,
        milestones: Sequence[Milestone],
        availability: Any,
        learner_profile: Any,
        existing_tasks: Sequence[Any] = (),
        kb_concepts: Sequence[LearningConcept] = (),
        kb_graphs: Sequence[ConceptPrerequisiteGraph] = (),
        daily_workload_cap_minutes: int | None = None,
        include_precomputed_budget: bool = True,
        reference_date: date | None = None,
    ) -> str:
        safe_title = format_untrusted_block(UntrustedBlockKind.GOAL_TITLE, goal.title)
        safe_desc = format_untrusted_block(
            UntrustedBlockKind.GOAL_RAW_DESCRIPTION,
            goal.raw_description or "Chưa có mô tả chi tiết.",
        )
        user_clar_lines, assumption_lines = cls._format_clarification_payload(
            goal.clarification_context, goal.prior_knowledge_level
        )

        milestone_payload = [
            {
                "milestone_id": str(m.id),
                "sequence_order": m.sequence_order,
                "title": sanitize_untrusted_text(m.title),
                "description": sanitize_untrusted_text(m.description or ""),
                "learning_outcomes": [
                    sanitize_untrusted_text(outcome)
                    for outcome in getattr(m, "learning_outcomes", ())
                ],
                "completion_criteria": sanitize_untrusted_text(
                    getattr(m, "completion_criteria", None) or ""
                ),
                "estimated_effort_minutes": int(getattr(m, "estimated_effort_minutes", 60)),
                "required_concepts": [
                    sanitize_untrusted_text(c) for c in getattr(m, "required_concepts", ())
                ],
                "unverified_concepts": [
                    sanitize_untrusted_text(c) for c in getattr(m, "unverified_concepts", ())
                ],
                "prerequisite_milestone_ids": [
                    str(pid) for pid in (getattr(m, "prerequisite_milestone_ids", ()) or ())
                ],
            }
            for m in sorted(milestones, key=lambda item: item.sequence_order)
        ]

        default_quota = getattr(availability, "default_daily_quota_minutes", None)
        if default_quota is None:
            default_quota = getattr(availability, "daily_cap_minutes", 120)

        avail_summary: dict[str, Any] = {
            "mode": getattr(availability, "mode", "MODE_A"),
            "default_daily_quota_minutes": int(default_quota if default_quota is not None else 120),
            "daily_quota_minutes": dict(getattr(availability, "daily_quota_minutes", {}) or {}),
            "disabled_weekdays": sorted(
                str(d) for d in (getattr(availability, "disabled_weekdays", ()) or ())
            ),
            "availability_slots": [
                _serialize_availability_slot(slot)
                for slot in (getattr(availability, "availability_slots", ()) or ())
            ],
            "timezone": getattr(availability, "timezone", "UTC"),
        }
        weekly_capacity = getattr(availability, "weekly_capacity_minutes", None)
        if weekly_capacity is not None:
            avail_summary["weekly_capacity_minutes"] = int(weekly_capacity)

        # D2: Never expose estimation_bias_beta to the LLM; deterministic scheduler owns beta.
        profile_summary = {
            "opt_session_minutes": int(getattr(learner_profile, "opt_session_minutes", 45)),
            "peak_productivity_slots": sanitize_untrusted_value(
                getattr(learner_profile, "peak_productivity_slots", {})
            ),
        }

        existing_summary = [
            {
                "task_id": str(getattr(t, "task_id", "")),
                "scheduled_date": (
                    t.scheduled_date.isoformat()
                    if getattr(t, "scheduled_date", None) is not None
                    else None
                ),
                "estimated_minutes": getattr(t, "estimated_minutes", 0),
                "scheduled_start": (
                    t.scheduled_start.isoformat()
                    if getattr(t, "scheduled_start", None) is not None
                    else None
                ),
                "scheduled_end": (
                    t.scheduled_end.isoformat()
                    if getattr(t, "scheduled_end", None) is not None
                    else None
                ),
            }
            for t in existing_tasks
        ]

        kb_lines = cls._format_kb_evidence(kb_concepts=kb_concepts, kb_graphs=kb_graphs)

        budget_lines: list[str] = []
        if include_precomputed_budget:
            effective_start_date = roadmap.start_date or reference_date or datetime.now(UTC).date()
            effective_target_date = (
                roadmap.target_date if roadmap.target_date is not None else goal.target_date
            )
            budget_summary = cls.compute_schedule_budget(
                availability=availability,
                milestones=milestones,
                start_date=effective_start_date,
                target_date=effective_target_date,
                learner_profile=learner_profile,
                existing_tasks=existing_tasks,
                daily_workload_cap_minutes=daily_workload_cap_minutes,
            )
            budget_lines.append(
                f"precomputed_schedule_budget: {json.dumps(budget_summary, ensure_ascii=False)}"
            )

        raw_prelim = (
            roadmap.planning_metadata.get("preliminary_feasibility")
            if isinstance(getattr(roadmap, "planning_metadata", None), dict)
            else None
        )
        if isinstance(raw_prelim, dict):
            prelim_summary = {
                "status": raw_prelim.get("status"),
                "scope_proposal_version": raw_prelim.get("scope_proposal_version"),
                "scope_approval_status": raw_prelim.get("scope_approval_status"),
                "hard_packable_capacity_minutes": raw_prelim.get("hard_packable_capacity_minutes"),
                "soft_target_capacity_minutes": raw_prelim.get("soft_target_capacity_minutes"),
                "normalized_planned_total_minutes": raw_prelim.get(
                    "normalized_planned_total_minutes"
                ),
                "kept_sequence_orders": [
                    int(item["sequence_order"])
                    for item in (raw_prelim.get("kept_scope") or [])
                    if isinstance(item, dict) and "sequence_order" in item
                ],
                "deferred_sequence_orders": [
                    int(item["sequence_order"])
                    for item in (raw_prelim.get("deferred_scope") or [])
                    if isinstance(item, dict) and "sequence_order" in item
                ],
            }
            budget_lines.append(
                f"preliminary_feasibility_summary: {json.dumps(prelim_summary, ensure_ascii=False)}"
            )

        sections = [
            "[USER_PROVIDED_FACTS]",
            safe_title,
            safe_desc,
            f"prior_knowledge_level: {goal.prior_knowledge_level}",
            f"target_date: {goal.target_date.isoformat() if goal.target_date else 'UNSPECIFIED'}",
            *user_clar_lines,
            "",
            "[SYSTEM_DERIVED_FACTS]",
            f"roadmap_id: {roadmap.id}",
            f"roadmap_start_date: {roadmap.start_date.isoformat() if roadmap.start_date else 'UNSPECIFIED'}",
            f"roadmap_target_date: {roadmap.target_date.isoformat() if roadmap.target_date else 'UNSPECIFIED'}",
            f"approved_milestones: {json.dumps(milestone_payload, ensure_ascii=False, default=str)}",
            f"availability_constraints: {json.dumps(avail_summary, ensure_ascii=False, default=str)}",
            f"learner_profile: {json.dumps(profile_summary, ensure_ascii=False, default=str)}",
            f"existing_committed_tasks: {json.dumps(existing_summary, ensure_ascii=False, default=str)}",
            *budget_lines,
            "",
            "[KNOWLEDGE_BASE_EVIDENCE]",
            *kb_lines,
            "",
            "[AI_ASSUMPTIONS_AND_UNKNOWNS]",
            *assumption_lines,
            "instruction: Phân rã thành các nhiệm vụ học tập nguyên tử (30 <= estimated_minutes <= 120) có learning_objective, completion_criteria, task_type (THEORY | PRACTICE | REVIEW | PROJECT) và dependencies không chu trình.",
        ]
        return "\n".join(sections)

    @staticmethod
    def format_learner_memory_layer(
        memory_items: Sequence[Any] = (),
        concept_masteries: Sequence[Any] = (),
    ) -> dict[str, Any]:
        """Serialize active LearnerMemoryItem & ConceptMastery snapshots for USER layer."""
        serialized_memories: list[dict[str, Any]] = []
        for item in memory_items:
            if isinstance(item, dict):
                key = str(item.get("memory_key", "")).strip()
                val = item.get("memory_value", {})
                cat = str(item.get("category", "PREFERENCE"))
                conf = float(item.get("confidence", 0.5))
            else:
                key = str(getattr(item, "memory_key", "")).strip()
                val = getattr(item, "memory_value", {})
                cat = str(getattr(item, "category", "PREFERENCE"))
                conf = float(getattr(item, "confidence", 0.5))
            if key:
                serialized_memories.append(
                    {
                        "category": cat,
                        "key": sanitize_untrusted_text(key)[:120],
                        "value": sanitize_untrusted_value(val),
                        "confidence": round(conf, 3),
                    }
                )

        serialized_masteries: list[dict[str, Any]] = []
        for mastery in concept_masteries:
            if isinstance(mastery, dict):
                ckey = str(mastery.get("concept_key", "")).strip()
                score = float(mastery.get("mastery_score", 0.0))
                ev = str(mastery.get("last_evidence_type", ""))
            else:
                ckey = str(getattr(mastery, "concept_key", "")).strip()
                score = float(getattr(mastery, "mastery_score", 0.0))
                ev = str(getattr(mastery, "last_evidence_type", ""))
            if ckey:
                serialized_masteries.append(
                    {
                        "concept_key": sanitize_untrusted_text(ckey)[:120],
                        "mastery_score": round(score, 3),
                        "evidence": sanitize_untrusted_text(ev),
                    }
                )
        return {
            "active_memories": serialized_memories,
            "concept_masteries": serialized_masteries,
        }

    @staticmethod
    def format_rag_learning_layer(
        knowledge_chunks: Sequence[Any] = (),
    ) -> list[dict[str, Any]]:
        """Wrap retrieved RAG KnowledgeChunks inside `<untrusted_knowledge_context>`."""
        wrapped_chunks: list[dict[str, Any]] = []
        for idx, chunk in enumerate(knowledge_chunks, start=1):
            if isinstance(chunk, dict):
                source_id = str(chunk.get("source_id", f"rag-{idx}"))
                chunk_index = chunk.get("chunk_index", idx - 1)
                content = str(chunk.get("content", "")).strip()
            else:
                source_id = str(getattr(chunk, "source_id", f"rag-{idx}"))
                chunk_index = getattr(chunk, "chunk_index", idx - 1)
                content = str(getattr(chunk, "content", "")).strip()
            if not content:
                continue
            citation_id = f"{source_id}#chunk-{chunk_index}"
            wrapped = wrap_untrusted_knowledge_context(
                source_id=citation_id,
                content=content[:1500],
            )
            wrapped_chunks.append({"citation_id": citation_id, "context": wrapped})
        return wrapped_chunks

    @classmethod
    def assemble_harness_context(
        cls,
        *,
        system_instruction: str = "",
        workflow_stage: str,
        base_context_text: str,
        learner_diagnostic: dict[str, Any] | None = None,
        workflow_constraints: dict[str, Any] | None = None,
        memory_items: Sequence[Any] = (),
        concept_masteries: Sequence[Any] = (),
        knowledge_chunks: Sequence[Any] = (),
        runtime_feedback: str = "",
        total_token_budget: int = 8000,
        include_planning_context: bool = True,
    ) -> AssembledContext:
        """Assemble non-redundant HarnessContext layers through shared `ContextEngine`.

        Caller sends `system_prompt` separately to `LLMProviderPort`; `system_instruction` is
        accepted only for call-site compatibility and intentionally excluded from the user
        context payload (D3) so the instruction is never duplicated.
        """
        del system_instruction
        user_payload = {
            k: sanitize_untrusted_value(v)
            for k, v in (learner_diagnostic or {}).items()
            if k not in {"estimation_bias_beta", "estimation_bias_factor"}
        }
        user_payload.update(cls.format_learner_memory_layer(memory_items, concept_masteries))

        rag_chunks = cls.format_rag_learning_layer(knowledge_chunks)
        learning_payload: dict[str, Any] = {}
        if include_planning_context:
            learning_payload["planning_context"] = base_context_text
            learning_payload["rag_chunks"] = rag_chunks
        elif rag_chunks:
            learning_payload["rag_chunks"] = rag_chunks
        workflow_payload: dict[str, Any] = {
            "stage": workflow_stage,
            **{
                k: sanitize_untrusted_value(v)
                for k, v in (workflow_constraints or {}).items()
                if k not in {"estimation_bias_beta", "estimation_bias_factor"}
            },
        }
        runtime_payload: dict[str, Any] = {}
        if runtime_feedback.strip():
            runtime_payload["feedback"] = sanitize_untrusted_text(runtime_feedback.strip())

        engine = ContextEngine(total_token_budget=total_token_budget)
        return engine.assemble(
            HarnessContext(
                system={},
                workflow=workflow_payload,
                user=user_payload,
                learning=learning_payload,
                runtime=runtime_payload,
            )
        )


GoalContextBuilder = RoadmapContextBuilder
