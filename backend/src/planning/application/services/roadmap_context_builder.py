import json
from collections.abc import Sequence
from typing import Any

from src.planning.application.dtos.planning_dtos import (
    ClarificationContextPayload,
    parse_clarification_context,
)
from src.planning.application.knowledge.untrusted_context import (
    wrap_untrusted_knowledge_context,
)
from src.planning.domain.models.goal import Goal
from src.planning.domain.models.knowledge_concept import (
    ConceptPrerequisiteGraph,
    LearningConcept,
)
from src.planning.domain.models.milestone import Milestone
from src.planning.domain.models.roadmap import Roadmap
from src.shared_kernel.application.harness.context_engine import (
    AssembledContext,
    ContextEngine,
)
from src.shared_kernel.application.harness.models import HarnessContext
from src.shared_kernel.infrastructure.external_ai.prompt_sanitizer import (
    PromptSanitizer,
)


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
        """Identify diagnostic dimensions already explicitly covered by the learner's Goal."""
        known: list[str] = []
        raw_lower = (goal.raw_description or "").lower()
        title_lower = (goal.title or "").lower()
        combined = f"{title_lower} {raw_lower}"

        if goal.target_date is not None or any(
            kw in combined
            for kw in ("tháng", "tuần", "ngày", "deadline", "hạn chót", "weeks", "months")
        ):
            known.append("TIMELINE_URGENCY")

        if any(
            kw in combined
            for kw in (
                "đã biết",
                "kinh nghiệm",
                "từng làm",
                "nền tảng",
                "chưa biết",
                "mới bắt đầu",
                "năm kinh nghiệm",
                "background",
            )
        ):
            known.append("PRIOR_EXPOSURE")

        if any(
            kw in combined
            for kw in (
                "dự án",
                "project",
                "thi",
                "phỏng vấn",
                "interview",
                "chứng chỉ",
                "đi làm",
                "thực tập",
                "capstone",
            )
        ):
            known.append("TARGET_OUTCOME")

        if any(
            kw in combined
            for kw in (
                "giờ/ngày",
                "phút/ngày",
                "buổi tối",
                "cuối tuần",
                "hours/day",
                "lịch học",
            )
        ):
            known.append("TIME_COMMITMENT")

        parsed = parse_clarification_context(goal.clarification_context)
        if parsed.answers:
            known.append("CLARIFICATION_ANSWERED")

        return known

    @classmethod
    def _format_clarification_payload(
        cls, raw_clarification: str | None, prior_level: str
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
                q_id = str(item.get("question_id", "")).strip()
                q_txt = PromptSanitizer.sanitize_text(str(item.get("question_text", "")))
                ans_txt = PromptSanitizer.sanitize_text(str(item.get("answer", "")))
                user_lines.append(f"  - [{q_id}] {q_txt} => {ans_txt}")
        elif parsed.synthesized_text and parsed.status == "ANSWERED":
            sanitized_text = PromptSanitizer.sanitize_text(parsed.synthesized_text)
            user_lines.append(f"clarification_notes: {sanitized_text}")

        if parsed.skipped_questions:
            assumption_lines.append(f"skipped_questions: {', '.join(parsed.skipped_questions)}")

        if parsed.unresolved_assumptions:
            for assumption_item in parsed.unresolved_assumptions:
                assumption_lines.append(
                    f"unresolved_assumption: {PromptSanitizer.sanitize_text(assumption_item)}"
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
            outcomes_str = "; ".join(c.learning_outcomes[:2])
            lines.append(
                f"- concept_id={c.concept_id} | title={c.title} | domain={c.domain} | "
                f"level={c.difficulty_level} | effort_min={c.estimated_effort_minutes} | "
                f"status={c.verification_status.value} | outcomes={outcomes_str}"
            )

        all_edges: list[str] = []
        unresolved: set[str] = set()
        for g in kb_graphs:
            for e in g.edges:
                all_edges.append(
                    f"  * {e.prerequisite_concept_id} --({e.relation_type.value}, depth={e.depth})--> {e.source_concept_id}: {e.rationale}"
                )
            for u in g.unresolved_ids:
                unresolved.add(u)

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
    ) -> str:
        safe_title = PromptSanitizer.sanitize_and_wrap("goal_title", goal.title)
        safe_desc = PromptSanitizer.sanitize_and_wrap(
            "goal_raw_description",
            goal.raw_description or "Chưa có mô tả chi tiết.",
        )
        known_dims = cls.extract_known_diagnostic_dimensions(goal)
        user_clar_lines, assumption_lines = cls._format_clarification_payload(
            goal.clarification_context, goal.prior_knowledge_level
        )

        system_lines = [
            f"goal_id: {goal.id}",
            f"known_diagnostic_dimensions: {json.dumps(known_dims, ensure_ascii=False)}",
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
        safe_title = PromptSanitizer.sanitize_and_wrap("goal_title", goal.title)
        safe_desc = PromptSanitizer.sanitize_and_wrap(
            "goal_raw_description",
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
            beta = getattr(learner_profile, "estimation_bias_beta", None)
            if opt_min is not None:
                sys_lines.append(f"opt_session_minutes: {opt_min}")
            if beta is not None:
                sys_lines.append(f"estimation_bias_beta: {beta}")

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
    ) -> str:
        safe_title = PromptSanitizer.sanitize_and_wrap("goal_title", goal.title)
        safe_desc = PromptSanitizer.sanitize_and_wrap(
            "goal_raw_description",
            goal.raw_description or "Chưa có mô tả chi tiết.",
        )
        user_clar_lines, assumption_lines = cls._format_clarification_payload(
            goal.clarification_context, goal.prior_knowledge_level
        )

        milestone_payload = [
            {
                "milestone_id": str(m.id),
                "sequence_order": m.sequence_order,
                "title": PromptSanitizer.sanitize_text(m.title),
                "description": PromptSanitizer.sanitize_text(m.description or ""),
            }
            for m in sorted(milestones, key=lambda item: item.sequence_order)
        ]

        avail_summary = {
            "mode": getattr(availability, "mode", "QUOTA"),
            "daily_cap_minutes": getattr(availability, "daily_cap_minutes", 120),
            "weekly_capacity_minutes": getattr(availability, "weekly_capacity_minutes", 600),
            "daily_quota_minutes": getattr(availability, "daily_quota_minutes", {}),
            "disabled_weekdays": list(getattr(availability, "disabled_weekdays", ())),
            "availability_slots": list(getattr(availability, "availability_slots", ())),
        }

        profile_summary = {
            "opt_session_minutes": getattr(learner_profile, "opt_session_minutes", 45),
            "estimation_bias_beta": getattr(learner_profile, "estimation_bias_beta", 1.0),
            "peak_productivity_slots": getattr(learner_profile, "peak_productivity_slots", {}),
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
                "planned_start_at": (
                    t.planned_start_at.isoformat()
                    if getattr(t, "planned_start_at", None) is not None
                    else None
                ),
                "planned_end_at": (
                    t.planned_end_at.isoformat()
                    if getattr(t, "planned_end_at", None) is not None
                    else None
                ),
            }
            for t in existing_tasks
        ]

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
            f"roadmap_id: {roadmap.id}",
            f"roadmap_start_date: {roadmap.start_date.isoformat() if roadmap.start_date else 'UNSPECIFIED'}",
            f"roadmap_target_date: {roadmap.target_date.isoformat() if roadmap.target_date else 'UNSPECIFIED'}",
            f"approved_milestones: {json.dumps(milestone_payload, ensure_ascii=False, default=str)}",
            f"availability_constraints: {json.dumps(avail_summary, ensure_ascii=False, default=str)}",
            f"learner_profile: {json.dumps(profile_summary, ensure_ascii=False, default=str)}",
            f"existing_committed_tasks: {json.dumps(existing_summary, ensure_ascii=False, default=str)}",
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
                        "key": PromptSanitizer.sanitize(key)[:120],
                        "value": val,
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
                        "concept_key": PromptSanitizer.sanitize(ckey)[:120],
                        "mastery_score": round(score, 3),
                        "evidence": ev,
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
                content=PromptSanitizer.sanitize(content)[:1500],
            )
            wrapped_chunks.append({"citation_id": citation_id, "context": wrapped})
        return wrapped_chunks

    @classmethod
    def assemble_harness_context(
        cls,
        *,
        system_instruction: str,
        workflow_stage: str,
        base_context_text: str,
        learner_diagnostic: dict[str, Any] | None = None,
        workflow_constraints: dict[str, Any] | None = None,
        memory_items: Sequence[Any] = (),
        concept_masteries: Sequence[Any] = (),
        knowledge_chunks: Sequence[Any] = (),
        runtime_feedback: str = "",
        total_token_budget: int = 8000,
    ) -> AssembledContext:
        """Assemble 5-layer HarnessContext through shared `ContextEngine`."""
        user_payload = dict(learner_diagnostic or {})
        user_payload.update(cls.format_learner_memory_layer(memory_items, concept_masteries))

        learning_payload: dict[str, Any] = {
            "planning_context": base_context_text,
            "rag_chunks": cls.format_rag_learning_layer(knowledge_chunks),
        }
        workflow_payload: dict[str, Any] = {
            "stage": workflow_stage,
            **(workflow_constraints or {}),
        }
        runtime_payload: dict[str, Any] = {}
        if runtime_feedback.strip():
            runtime_payload["feedback"] = runtime_feedback.strip()

        engine = ContextEngine(total_token_budget=total_token_budget)
        return engine.assemble(
            HarnessContext(
                system={"instruction": system_instruction},
                workflow=workflow_payload,
                user=user_payload,
                learning=learning_payload,
                runtime=runtime_payload,
            )
        )


GoalContextBuilder = RoadmapContextBuilder
