import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from src.planning.application.dtos.planning_dtos import (
    ClarificationFollowupLLMOutput,
    ClarificationQuestionsLLMOutput,
    CriticQualityLLMOutput,
    MilestoneGenerationLLMOutput,
    PedagogicalJudgeLLMOutput,
    TaskProposalLLMOutput,
)
from src.planning.application.services.knowledge_tool_dispatcher import (
    ALL_KNOWLEDGE_TOOL_DECLARATIONS,
    RoadmapPipelineStage,
)
from src.planning.application.services.knowledge_tool_dispatcher import (
    STAGE_ALLOWED_TOOLS as _DISPATCHER_STAGE_ALLOWED_TOOLS,
)
from src.shared_kernel.application.harness.models import PromptTemplate, WorkflowType
from src.shared_kernel.application.harness.prompt_registry import PromptRegistry
from src.shared_kernel.application.harness.untrusted_context import (
    UNTRUSTED_DATA_SYSTEM_RULE,
    UntrustedBlockKind,
    format_untrusted_block,
    redact_sensitive_keys,
    sanitize_untrusted_text,
    sanitize_untrusted_value,
)


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    """Versioned pedagogical skill contract for FocusFlow AI Roadmap Generation."""

    skill_id: str
    version: str
    title: str
    stage: RoadmapPipelineStage
    allowed_tools: tuple[str, ...]
    thinking_level: str
    max_tool_calls: int
    system_instruction: str


@dataclass(frozen=True, slots=True)
class AuxiliaryPromptDefinition:
    """Versioned prompt contract for auxiliary planning stages (follow-up, critics, retry)."""

    prompt_id: str
    version: str
    workflow_type: str
    skill_id: str
    thinking_level: str
    system_instruction: str
    output_model: type[Any]


GOAL_CLARIFIER_SKILL = SkillDefinition(
    skill_id="goal-clarifier",
    version="2.0.0",
    title="Chuyên gia Chẩn đoán & Làm rõ Mục tiêu Học tập (SRL Forethought)",
    stage=RoadmapPipelineStage.GOAL_CLARIFICATION,
    allowed_tools=(),
    thinking_level="LOW",
    max_tool_calls=0,
    system_instruction=(
        "[SKILL: goal-clarifier@v2.0.0]\n"
        f"{UNTRUSTED_DATA_SYSTEM_RULE}\n"
        "Bạn là Chuyên gia Chẩn đoán Mục tiêu Học tập của FocusFlow theo mô hình SRL Zimmerman.\n"
        "Nhiệm vụ: Phân tích facts có provenance và danh sách information gaps để sinh tối đa số câu hỏi "
        "chẩn đoán bằng tiếng Việt (tối đa 3 câu; số câu hỏi <= số gaps; trả 0 câu nếu không còn gap nào).\n"
        "Quy tắc bắt buộc:\n"
        "1. Chiều chẩn đoán chuẩn (`diagnostic_dimension`) CHỈ được lấy từ 7 giá trị: "
        "`TARGET_OUTCOME`, `PRIOR_KNOWLEDGE`, `PRACTICAL_EXPERIENCE`, `TIME_COMMITMENT`, "
        "`TIMELINE`, `DESIRED_DEPTH`, `LEARNING_PREFERENCE`.\n"
        "2. Ưu tiên câu hỏi trắc nghiệm (`single_choice` hoặc `multiple_choice`) với tối đa 4 phương án "
        "chuyên môn cụ thể, tách biệt hoàn toàn và không chồng lấn ngữ nghĩa (máy chủ sẽ tự bổ sung phương án 'Khác' ở cuối). "
        "Chỉ dùng tối đa 1 câu `text` (`options: []`) khi cần người học tự mô tả sản phẩm đầu ra.\n"
        "3. Mỗi câu hỏi bắt buộc nêu rõ `question_purpose` (vì sao thông tin này quyết định cấu trúc lộ trình) "
        "và `expected_answer_format` (cách người học nên phản hồi).\n"
        "4. TUYỆT ĐỐI không hỏi lại thông tin đã có trong `[USER_PROVIDED_FACTS]` hoặc `known_diagnostic_dimensions`.\n"
        "5. Không gọi công cụ và không xuất suy luận nội bộ ngoài cấu trúc dữ liệu."
    ),
)

MILESTONE_PLANNER_SKILL = SkillDefinition(
    skill_id="learning-milestone-planner",
    version="2.0.0",
    title="Kiến trúc sư Lộ trình Cột mốc Học thuật (SRL Forethought)",
    stage=RoadmapPipelineStage.MILESTONE_PLANNING,
    allowed_tools=("search_learning_concepts", "get_concept_prerequisite_graph"),
    thinking_level="LOW",
    max_tool_calls=4,
    system_instruction=(
        "[SKILL: learning-milestone-planner@v2.0.0]\n"
        f"{UNTRUSTED_DATA_SYSTEM_RULE}\n"
        "Bạn là Kiến trúc sư Lộ trình Học tập Thích ứng của FocusFlow.\n"
        "Nhiệm vụ: Thiết kế chuỗi cột mốc kiến thức tuần tự (`milestones`, `sequence_order` liên tục từ 1) bằng tiếng Việt.\n"
        "Quy tắc bắt buộc:\n"
        "1. Chống bịa mã khái niệm: `required_concepts` CHỈ được chứa `concept_id` tồn tại trong `[KNOWLEDGE_BASE_EVIDENCE]` "
        "hoặc kết quả tool `search_learning_concepts` / `get_concept_prerequisite_graph`. Mọi khái niệm cần học ngoài catalog "
        "BẮT BUỘC đặt vào `unverified_concepts`, tuyệt đối không tự bịa mã khái niệm.\n"
        "2. Tiêu chí bao phủ (Coverage Criteria): Lập coverage blueprint nội bộ từ mục tiêu đầu ra về kiến thức nền; "
        "không trùng lặp giữa các cột mốc, không bỏ sót kỹ năng cốt lõi. Mỗi cột mốc phải có `learning_outcomes` cụ thể "
        "(sẽ gán mã `M{sequence_order}-O{index}`) và `completion_criteria` đo lường được.\n"
        "3. Giới hạn nỗ lực (`estimated_effort_minutes`): >= 15 phút/cột mốc (khuyến nghị 60..600 phút tùy độ lớn thực tế), "
        "phân bổ cân xứng với số task 30..120 phút.\n"
        "4. Chiến lược phạm vi:\n"
        "   - `FULL_SCOPE`: Bao phủ toàn bộ mục tiêu gốc trong `milestones`, `scope_summary` tóm tắt toàn bộ lộ trình, `deferred_scope` là `[]`.\n"
        "   - `FIT_CAPACITY`: Thu hẹp `milestones` về phạm vi khả thi nhất theo quỹ thời gian/deadline; `scope_summary` nêu rõ phạm vi giữ lại "
        "và giới hạn hiện tại; `deferred_scope` liệt kê tường minh các nội dung bị hoãn lại và KHÔNG tuyên bố đạt toàn bộ mục tiêu gốc.\n"
        "5. Không xuất suy luận nội bộ; chỉ xuất cấu trúc dữ liệu hợp lệ."
    ),
)

TASK_DECOMPOSER_SKILL = SkillDefinition(
    skill_id="learning-task-decomposer",
    version="2.0.0",
    title="Chuyên gia Phân rã Nhiệm vụ Học tập Nguyên tử (SRL Performance Prep)",
    stage=RoadmapPipelineStage.TASK_DECOMPOSITION,
    allowed_tools=(
        "search_learning_concepts",
        "get_concept_prerequisite_graph",
        "get_learning_resources_and_guidance",
    ),
    thinking_level="LOW",
    max_tool_calls=4,
    system_instruction=(
        "[SKILL: learning-task-decomposer@v2.0.0]\n"
        f"{UNTRUSTED_DATA_SYSTEM_RULE}\n"
        "Bạn là Chuyên gia Phân rã Nhiệm vụ Học tập Nguyên tử của FocusFlow.\n"
        "Quy trình tư duy gồm 2 bước tách biệt:\n"
        "- Bước 1 — Tra cứu (Tool Discovery): Khi được cung cấp khai báo công cụ, gọi `search_learning_concepts`, "
        "`get_concept_prerequisite_graph` và `get_learning_resources_and_guidance` để thu thập `concept_ids` và `resource_ids` xác thực.\n"
        "- Bước 2 — Xuất kết quả (Final Output): Không gọi thêm công cụ nào; tạo `tasks` và đồ thị DAG `dependencies`.\n"
        "Quy tắc bắt buộc:\n"
        "1. `task_id` tuần tự dạng `T1, T2, T3, ...`; gắn đúng `milestone_id` của cột mốc `APPROVED`.\n"
        "2. Tiến trình sư phạm chuẩn theo thứ tự `THEORY -> PRACTICE -> REVIEW -> PROJECT`: nắm lý thuyết nền trước, "
        "thực hành áp dụng, ôn tập củng cố rồi tổng hợp dự án.\n"
        "3. Mỗi nhiệm vụ có `30 <= estimated_minutes <= 120`, tôn trọng `opt_session_minutes` và sử dụng trực tiếp "
        "`estimated_effort_minutes` đã tính sẵn từ ngữ cảnh milestone.\n"
        "4. `resource_ids` chứa tối đa 3 ID trích nguyên văn từ kết quả tool `get_learning_resources_and_guidance` (để `[]` nếu tool không có); "
        "tuyệt đối không tự bịa ID hay URL.\n"
        "5. Bao phủ 100% `M{seq}-O{i}` trong `covered_outcome_ids` và `required_concepts` trong `concept_ids`; "
        "`dependencies` phải là DAG không chu trình. Không sinh `scheduled_date`, `scheduled_start`, `scheduled_end`."
    ),
)

PEDAGOGICAL_JUDGE_SKILL = SkillDefinition(
    skill_id="pedagogical-quality-judge",
    version="2.0.0",
    title="Giám khảo Thẩm định Sư phạm Tầng 3 (Tier 3 Pedagogical Judge)",
    stage=RoadmapPipelineStage.PEDAGOGICAL_JUDGE,
    allowed_tools=(),
    thinking_level="LOW",
    max_tool_calls=0,
    system_instruction=(
        "[SKILL: pedagogical-quality-judge@v2.0.0]\n"
        f"{UNTRUSTED_DATA_SYSTEM_RULE}\n"
        "Bạn là Giám khảo Thẩm định Chất lượng Sư phạm độc lập (Tier 3) của FocusFlow.\n"
        "Thang điểm Rubric 0..100 neo các mốc chuẩn:\n"
        "- `0` (0..39): Sai thứ tự tiên quyết nghiêm trọng, thiếu phủ outcome/concept hoặc thiếu tiêu chí hoàn thành (`score < 60` => FAIL tại máy chủ).\n"
        "- `40` (40..59): Mất cân bằng nặng (ví dụ toàn THEORY thiếu thực hành), quá tải nhận thức hoặc mục tiêu mơ hồ (`score < 60` => FAIL tại máy chủ).\n"
        "- `60` (60..79): Đạt ngưỡng tối thiểu, thứ tự hợp lý, còn cảnh báo nhẹ (`WARNING`).\n"
        "- `80` (80..99): Tốt, xen kẽ `THEORY -> PRACTICE -> REVIEW -> PROJECT` cân đối, đo lường rõ.\n"
        "- `100`: Xuất sắc, không có lỗi sư phạm.\n"
        "Quy tắc bắt buộc:\n"
        "1. Đánh giá dựa trên trình độ người học (`learner_level`), tóm tắt cột mốc (`milestone_summary`) và bản đề xuất.\n"
        "2. Mọi `issue` bắt buộc có `evidence` cụ thể trích từ proposal và trỏ `task_ref` tới đúng `task_id` / UUID tồn tại trong proposal "
        "(chỉ để `task_ref: null` cho lỗi toàn cục như mất cân bằng loại task).\n"
        "3. `score < 60` hoặc có issue mức `CRITICAL` / `ERROR` / `FAIL` tương ứng kết luận FAIL ở máy chủ. Không gọi công cụ."
    ),
)

GOAL_CLARIFIER_FOLLOWUP_PROMPT = AuxiliaryPromptDefinition(
    prompt_id="goal-clarifier-followup",
    version="2.0.0",
    workflow_type=WorkflowType.PLAN_CREATION.value,
    skill_id=GOAL_CLARIFIER_SKILL.skill_id,
    thinking_level="LOW",
    output_model=ClarificationFollowupLLMOutput,
    system_instruction=(
        "[SKILL: goal-clarifier-followup@v2.0.0]\n"
        f"{UNTRUSTED_DATA_SYSTEM_RULE}\n"
        "Bạn là Chuyên gia Chẩn đoán Mục tiêu Học tập của FocusFlow (vòng Follow-up).\n"
        "Nhiệm vụ: Sinh DUY NHẤT 1 câu hỏi làm rõ sâu hơn bằng tiếng Việt cho đúng `information_gap` còn mở.\n"
        "Quy tắc bắt buộc:\n"
        "1. `diagnostic_dimension` phải khớp chính xác chiều của gap đang xử lý (thuộc 7 giá trị chuẩn `DiagnosticDimension`).\n"
        "2. Không lặp lại câu hỏi hoặc thông tin đã có trong câu trả lời vòng trước.\n"
        "3. Ưu tiên câu hỏi trắc nghiệm (`single_choice` hoặc `multiple_choice`) gồm tối đa 4 phương án chuyên môn "
        "không chồng lấn; nêu rõ `question_purpose` và `expected_answer_format`.\n"
        "4. Không gọi công cụ và không xuất suy luận nội bộ."
    ),
)

PROPOSAL_SELF_CORRECTION_PROMPT = AuxiliaryPromptDefinition(
    prompt_id="proposal-self-correction",
    version="2.0.0",
    workflow_type=WorkflowType.SCHEDULE_GENERATION.value,
    skill_id=TASK_DECOMPOSER_SKILL.skill_id,
    thinking_level="LOW",
    output_model=TaskProposalLLMOutput,
    system_instruction=(
        "[SKILL: proposal-self-correction@v2.0.0]\n"
        f"{UNTRUSTED_DATA_SYSTEM_RULE}\n"
        "Bạn đang ở bước Tự Sửa Lỗi Ràng Buộc (Self-Correction Retry).\n"
        "Bản đề xuất ở lần thử trước đã vi phạm các ràng buộc bắt buộc. Vì ngữ cảnh hiện tại không đính kèm payload cũ, "
        "bạn BẮT BUỘC sinh lại TOÀN BỘ danh sách hợp lệ từ đầu (đầy đủ cột mốc, outcomes, concepts và DAG không chu trình) "
        "và khắc phục TRIỆT ĐỂ mọi mã lỗi được liệt kê."
    ),
)

COVERAGE_PREREQUISITE_CRITIC_PROMPT = AuxiliaryPromptDefinition(
    prompt_id="coverage-prerequisite-critic",
    version="2.0.0",
    workflow_type=WorkflowType.SCHEDULE_GENERATION.value,
    skill_id="coverage-prerequisite-critic",
    thinking_level="LOW",
    output_model=CriticQualityLLMOutput,
    system_instruction=(
        "[SKILL: coverage-prerequisite-critic@v2.0.0]\n"
        f"{UNTRUSTED_DATA_SYSTEM_RULE}\n"
        "Bạn là AI Critic độc lập chuyên kiểm tra Độ bao phủ & Thứ tự Tiên quyết của FocusFlow.\n"
        "Nhiệm vụ: Kiểm tra độ phủ mục tiêu/khái niệm, phát hiện lỗ hổng, trùng lặp và đảo ngược thứ tự tiên quyết.\n"
        "Quy tắc: Không sửa payload, không suy đoán ngoài dữ liệu; mọi issue phải nêu rõ `evidence` trích từ payload "
        "và `task_ref` hợp lệ (nếu lỗi gắn với task/milestone cụ thể). Chỉ gắn `severity=ERROR` khi có bằng chứng xác thực."
    ),
)

LEARNER_FIT_CRITIC_PROMPT = AuxiliaryPromptDefinition(
    prompt_id="learner-fit-actionability-critic",
    version="2.0.0",
    workflow_type=WorkflowType.SCHEDULE_GENERATION.value,
    skill_id="learner-fit-actionability-critic",
    thinking_level="LOW",
    output_model=CriticQualityLLMOutput,
    system_instruction=(
        "[SKILL: learner-fit-actionability-critic@v2.0.0]\n"
        f"{UNTRUSTED_DATA_SYSTEM_RULE}\n"
        "Bạn là AI Critic độc lập chuyên kiểm tra Độ phù hợp Người học & Tính Hành động của FocusFlow.\n"
        "Nhiệm vụ: Đánh giá độ khớp với trình độ (`learner_level`), tải nhận thức, cân bằng `THEORY -> PRACTICE -> REVIEW -> PROJECT`, "
        "và tính đo lường được của mục tiêu/tiêu chí hoàn thành.\n"
        "Quy tắc: Không sửa payload; mọi issue phải nêu rõ `evidence` trích từ payload và `task_ref` hợp lệ nếu gắn với task cụ thể."
    ),
)

QUALITY_ARBITER_PROMPT = AuxiliaryPromptDefinition(
    prompt_id="quality-arbiter",
    version="2.0.0",
    workflow_type=WorkflowType.SCHEDULE_GENERATION.value,
    skill_id="quality-arbiter",
    thinking_level="LOW",
    output_model=CriticQualityLLMOutput,
    system_instruction=(
        "[SKILL: quality-arbiter@v2.0.0]\n"
        f"{UNTRUSTED_DATA_SYSTEM_RULE}\n"
        "Bạn là AI Quality Arbiter độc lập của FocusFlow.\n"
        "Nhiệm vụ: Phân xử bất đồng giữa hai Critic độc lập dựa trên bằng chứng đối chiếu trực tiếp trong payload và ngữ cảnh.\n"
        "Quy tắc: Chỉ giữ lại lỗi có `evidence` xác thực và `task_ref` tồn tại trong payload; loại bỏ nhận định cảm tính hoặc không có căn cứ."
    ),
)

ROADMAP_SKILL_REGISTRY: dict[str, SkillDefinition] = {
    GOAL_CLARIFIER_SKILL.skill_id: GOAL_CLARIFIER_SKILL,
    MILESTONE_PLANNER_SKILL.skill_id: MILESTONE_PLANNER_SKILL,
    TASK_DECOMPOSER_SKILL.skill_id: TASK_DECOMPOSER_SKILL,
    PEDAGOGICAL_JUDGE_SKILL.skill_id: PEDAGOGICAL_JUDGE_SKILL,
}

AUXILIARY_PLANNING_PROMPTS: dict[str, AuxiliaryPromptDefinition] = {
    GOAL_CLARIFIER_FOLLOWUP_PROMPT.prompt_id: GOAL_CLARIFIER_FOLLOWUP_PROMPT,
    PROPOSAL_SELF_CORRECTION_PROMPT.prompt_id: PROPOSAL_SELF_CORRECTION_PROMPT,
    COVERAGE_PREREQUISITE_CRITIC_PROMPT.prompt_id: COVERAGE_PREREQUISITE_CRITIC_PROMPT,
    LEARNER_FIT_CRITIC_PROMPT.prompt_id: LEARNER_FIT_CRITIC_PROMPT,
    QUALITY_ARBITER_PROMPT.prompt_id: QUALITY_ARBITER_PROMPT,
}

STAGE_ALLOWED_TOOLS: dict[RoadmapPipelineStage, frozenset[str]] = {
    skill.stage: frozenset(skill.allowed_tools) for skill in ROADMAP_SKILL_REGISTRY.values()
}


def verify_skill_stage_tool_authority(
    skills: dict[str, SkillDefinition] | None = None,
) -> dict[RoadmapPipelineStage, frozenset[str]]:
    """Verify and synchronize stage tool authority from `SkillDefinition.allowed_tools`."""
    source_skills = ROADMAP_SKILL_REGISTRY if skills is None else skills
    derived: dict[RoadmapPipelineStage, frozenset[str]] = {}
    known_tools = set(ALL_KNOWLEDGE_TOOL_DECLARATIONS.keys())
    for skill in source_skills.values():
        if skill.stage in derived:
            raise ValueError(f"Duplicate SkillDefinition for pipeline stage: {skill.stage.value}")
        unknown_tools = sorted(t for t in skill.allowed_tools if t not in known_tools)
        if unknown_tools:
            raise ValueError(f"Skill '{skill.skill_id}' references unknown tools: {unknown_tools}")
        derived[skill.stage] = frozenset(skill.allowed_tools)

    expected_stages = set(RoadmapPipelineStage)
    derived_stages = set(derived.keys())
    if derived_stages != expected_stages:
        missing = sorted(s.value for s in (expected_stages - derived_stages))
        raise ValueError(f"Missing SkillDefinition for pipeline stages: {missing}")

    if skills is None:
        _DISPATCHER_STAGE_ALLOWED_TOOLS.clear()
        _DISPATCHER_STAGE_ALLOWED_TOOLS.update(derived)
    return dict(derived)


verify_skill_stage_tool_authority()


def get_roadmap_skill(skill_id: str) -> SkillDefinition:
    """Look up a registered roadmap skill by its canonical ID."""
    if skill_id not in ROADMAP_SKILL_REGISTRY:
        raise KeyError(f"Unknown roadmap skill_id: {skill_id}")
    return ROADMAP_SKILL_REGISTRY[skill_id]


def build_goal_clarifier_prompt(
    context_block: str = "",
    *,
    goal_title: str = "",
    raw_description: str = "",
    prior_knowledge_level: str = "BEGINNER",
    target_date_iso: str | None = None,
    known_dimensions: Sequence[str] = (),
    gap_count: int | None = None,
) -> str:
    """Build user prompt for `goal-clarifier` with untrusted facts first and action request last (T6.4)."""
    extra_facts: list[str] = []
    if not context_block.strip():
        if goal_title:
            extra_facts.append(format_untrusted_block(UntrustedBlockKind.GOAL_TITLE, goal_title))
        if raw_description:
            extra_facts.append(
                format_untrusted_block(UntrustedBlockKind.GOAL_RAW_DESCRIPTION, raw_description)
            )
        if prior_knowledge_level:
            extra_facts.append(
                f"prior_knowledge_level: {sanitize_untrusted_text(prior_knowledge_level)}"
            )
        if target_date_iso:
            extra_facts.append(f"target_date: {sanitize_untrusted_text(target_date_iso)}")
    if known_dimensions:
        safe_dims = ", ".join(sanitize_untrusted_text(str(d)) for d in known_dimensions)
        extra_facts.append(f"known_dimensions_do_not_repeat: {safe_dims}")

    parts: list[str] = [f"[SKILL: {GOAL_CLARIFIER_SKILL.skill_id}@v{GOAL_CLARIFIER_SKILL.version}]"]
    if context_block.strip():
        parts.append(context_block.strip())
    if extra_facts:
        parts.append("\n".join(extra_facts))

    max_q = min(3, max(0, gap_count)) if gap_count is not None else 3
    action_tail = (
        f"Yêu cầu hành động: Chỉ dựa vào các information gaps chưa biết ở trên, "
        f"hãy sinh tối đa {max_q} câu hỏi chẩn đoán bằng tiếng Việt "
        "(số câu hỏi <= số gaps; trả 0 câu nếu không còn gap). "
        "Mỗi câu trắc nghiệm gồm tối đa 4 phương án chuyên môn không chồng lấn, kèm `question_purpose`, "
        "`expected_answer_format` và `diagnostic_dimension` chuẩn; tuyệt đối không hỏi lại các chiều đã biết."
    )
    parts.append(action_tail)
    return "\n\n".join(parts)


def build_goal_clarifier_followup_prompt(
    *,
    gap: dict[str, Any],
    prior_answers: Sequence[dict[str, Any]],
) -> str:
    """Build structured, untrusted-isolated user prompt for round-2 clarification follow-up (T6.4)."""
    safe_gap_json = json.dumps(redact_sensitive_keys(gap), ensure_ascii=False, default=str)
    safe_answers_json = json.dumps(
        redact_sensitive_keys(list(prior_answers)), ensure_ascii=False, default=str
    )
    gap_block = format_untrusted_block(
        UntrustedBlockKind.CLARIFICATION_DATA,
        safe_gap_json,
        attributes={"kind": "information_gap"},
    )
    answers_block = format_untrusted_block(
        UntrustedBlockKind.LEARNER_ANSWER,
        safe_answers_json,
        attributes={"kind": "prior_answers"},
    )
    return (
        f"[SKILL: {GOAL_CLARIFIER_FOLLOWUP_PROMPT.prompt_id}@v{GOAL_CLARIFIER_FOLLOWUP_PROMPT.version}]\n"
        f"{gap_block}\n"
        f"{answers_block}\n\n"
        "Yêu cầu hành động: Sinh đúng 1 câu hỏi follow-up bằng tiếng Việt làm rõ information gap trên, "
        "không lặp câu đã hỏi, ưu tiên trắc nghiệm tối đa 4 lựa chọn chuyên môn không chồng lấn."
    )


def build_milestone_planner_prompt(
    context_block: str = "",
    *,
    goal_title: str = "",
    raw_description: str = "",
    prior_knowledge_level: str = "BEGINNER",
    clarification_summary: str = "",
    generation_strategy: str = "FULL_SCOPE",
) -> str:
    """Build user prompt for `learning-milestone-planner` with action instructions last (T6.5)."""
    extra_lines: list[str] = []
    if not context_block.strip():
        if goal_title:
            extra_lines.append(format_untrusted_block(UntrustedBlockKind.GOAL_TITLE, goal_title))
        if raw_description:
            extra_lines.append(
                format_untrusted_block(UntrustedBlockKind.GOAL_RAW_DESCRIPTION, raw_description)
            )
        if prior_knowledge_level:
            extra_lines.append(
                f"prior_knowledge_level: {sanitize_untrusted_text(prior_knowledge_level)}"
            )
        if clarification_summary:
            extra_lines.append(
                format_untrusted_block(UntrustedBlockKind.CLARIFICATION_DATA, clarification_summary)
            )

    strategy_clean = sanitize_untrusted_text(generation_strategy).upper() or "FULL_SCOPE"
    parts: list[str] = [
        f"[SKILL: {MILESTONE_PLANNER_SKILL.skill_id}@v{MILESTONE_PLANNER_SKILL.version}]"
    ]
    if context_block.strip():
        parts.append(context_block.strip())
    if extra_lines:
        parts.append("\n".join(extra_lines))

    parts.append(
        f"Generation strategy: {strategy_clean}.\n"
        "Yêu cầu hành động: Thiết kế chuỗi cột mốc thích ứng (`sequence_order` liên tục từ 1), "
        "kèm `learning_outcomes`, `completion_criteria`, `estimated_effort_minutes` (>= 15), "
        "`required_concepts` (chỉ ID từ Knowledge Base / tool) và `unverified_concepts` (ngoài KB). "
        "Điền đầy đủ `scope_summary` và `deferred_scope` đúng theo chiến lược "
        f"({strategy_clean})."
    )
    return "\n\n".join(parts)


def build_task_decomposer_prompt(
    context_block: str = "",
    *,
    milestones_summary: str = "",
    availability_summary: str = "",
) -> str:
    """Build user prompt for `learning-task-decomposer` with 2-step guidance last (T6.1)."""
    extra_lines: list[str] = []
    if not context_block.strip():
        if milestones_summary:
            extra_lines.append(
                format_untrusted_block(UntrustedBlockKind.MILESTONE_DATA, milestones_summary)
            )
        if availability_summary:
            extra_lines.append(
                f"availability_constraints: {sanitize_untrusted_text(availability_summary)}"
            )

    parts: list[str] = [
        f"[SKILL: {TASK_DECOMPOSER_SKILL.skill_id}@v{TASK_DECOMPOSER_SKILL.version}]"
    ]
    if context_block.strip():
        parts.append(context_block.strip())
    if extra_lines:
        parts.append("\n".join(extra_lines))

    parts.append(
        "Yêu cầu hành động:\n"
        "- Bước 1 (Tra cứu): Khi có công cụ, tra cứu concepts & learning resources liên quan.\n"
        "- Bước 2 (Xuất kết quả): Phân rã các cột mốc APPROVED thành danh sách nhiệm vụ nguyên tử (`task_id` T1, T2, ...) "
        "theo tiến trình `THEORY -> PRACTICE -> REVIEW -> PROJECT`, mỗi nhiệm vụ 30..120 phút "
        "dựa theo effort và `opt_session_minutes` đã tính sẵn, chọn tối đa 3 `resource_ids` từ kết quả tool, "
        "bao phủ mọi `covered_outcome_ids` & `concept_ids`, và lập `dependencies` dạng DAG không chu trình."
    )
    return "\n\n".join(parts)


def build_compact_judge_payload(
    proposal_data: dict[str, Any],
    milestones_metadata: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Build compact Judge payload stripping noisy fields while keeping dependencies, objectives, and criteria."""
    raw_deps_input = proposal_data.get("dependencies")
    normalized_deps: list[dict[str, Any]] = []
    preds_by_task: dict[str, list[str]] = {}
    seen_edges: set[tuple[str, str]] = set()
    if isinstance(raw_deps_input, list):
        for dep in raw_deps_input:
            if not isinstance(dep, dict):
                continue
            pred = str(dep.get("predecessor_id") or "").strip()
            succ = str(dep.get("successor_id") or "").strip()
            if not pred or not succ:
                continue
            edge_key = (pred, succ)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                normalized_deps.append(
                    {
                        "predecessor_id": pred,
                        "successor_id": succ,
                        "is_mandatory": bool(dep.get("is_mandatory", True)),
                    }
                )
            preds_by_task.setdefault(succ, [])
            if pred not in preds_by_task[succ]:
                preds_by_task[succ].append(pred)

    compact_tasks: list[dict[str, Any]] = []
    raw_tasks = proposal_data.get("tasks")
    if isinstance(raw_tasks, list):
        for task in raw_tasks:
            if not isinstance(task, dict):
                continue
            raw_tid = task.get("task_id") if task.get("task_id") is not None else task.get("id")
            tid = str(raw_tid).strip() if raw_tid is not None else ""
            task_deps: list[str] = []
            for dep_key in ("depends_on_task_ids", "dependencies"):
                raw_t_deps = task.get(dep_key)
                if isinstance(raw_t_deps, (list, tuple)):
                    for item in raw_t_deps:
                        dep_id = (
                            str(item.get("predecessor_id") or item.get("task_id") or "").strip()
                            if isinstance(item, dict)
                            else str(item).strip()
                        )
                        if dep_id and dep_id not in task_deps:
                            task_deps.append(dep_id)
            if tid and tid in preds_by_task:
                for pred in preds_by_task[tid]:
                    if pred not in task_deps:
                        task_deps.append(pred)
            if tid:
                for pred in task_deps:
                    edge_key = (pred, tid)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        normalized_deps.append(
                            {
                                "predecessor_id": pred,
                                "successor_id": tid,
                                "is_mandatory": True,
                            }
                        )

            compact_task: dict[str, Any] = {
                "task_id": tid,
                "milestone_id": str(task.get("milestone_id") or ""),
                "title": str(task.get("title") or ""),
                "task_type": str(task.get("task_type") or ""),
                "estimated_minutes": task.get("estimated_minutes"),
                "scheduled_date": task.get("scheduled_date"),
                "learning_objective": str(task.get("learning_objective") or ""),
                "completion_criteria": str(task.get("completion_criteria") or ""),
                "depends_on_task_ids": task_deps,
            }
            if "dependencies" in task:
                raw_task_deps = task["dependencies"]
                compact_task["dependencies"] = (
                    list(raw_task_deps)
                    if isinstance(raw_task_deps, (list, tuple))
                    else raw_task_deps
                )
            if task.get("covered_outcome_ids"):
                compact_task["covered_outcome_ids"] = list(task["covered_outcome_ids"])
            compact_tasks.append(compact_task)

    raw_milestones: list[Any]
    if milestones_metadata is not None:
        raw_milestones = list(milestones_metadata)
    elif isinstance(proposal_data.get("milestones"), list):
        raw_milestones = list(proposal_data["milestones"])
    else:
        raw_milestones = []

    compact_milestones: list[dict[str, Any]] = []
    for m in raw_milestones:
        if isinstance(m, dict):
            mid = str(m.get("milestone_id") or m.get("id") or "")
            seq = m.get("sequence_order")
            title = str(m.get("title") or "")
            raw_outcomes = m.get("learning_outcomes")
            outcomes = (
                [str(o) for o in raw_outcomes] if isinstance(raw_outcomes, (list, tuple)) else []
            )
            raw_obj = m.get("learning_objective")
            comp_criteria = str(m.get("completion_criteria") or "")
        else:
            mid = str(getattr(m, "id", getattr(m, "milestone_id", "")) or "")
            seq = getattr(m, "sequence_order", None)
            title = str(getattr(m, "title", "") or "")
            raw_outcomes = getattr(m, "learning_outcomes", ()) or ()
            outcomes = [str(o) for o in raw_outcomes]
            raw_obj = getattr(m, "learning_objective", None)
            comp_criteria = str(getattr(m, "completion_criteria", None) or "")

        m_entry: dict[str, Any] = {
            "milestone_id": mid,
            "sequence_order": seq,
            "title": title,
            "learning_outcomes": outcomes,
            "completion_criteria": comp_criteria,
        }
        if raw_obj is not None and str(raw_obj).strip():
            m_entry["learning_objective"] = str(raw_obj)
        compact_milestones.append(m_entry)

    compact_payload: dict[str, Any] = {
        "tasks": compact_tasks,
        "dependencies": normalized_deps,
    }
    if compact_milestones:
        compact_payload["milestones"] = compact_milestones
    return compact_payload


def build_pedagogical_judge_prompt(
    proposal_payload: dict[str, Any] | str,
    *,
    context_block: str = "",
    milestones_summary: str = "",
    learner_level: str = "",
    milestones_metadata: Sequence[Any] | None = None,
) -> str:
    """Build user prompt for `pedagogical-quality-judge` (Tier 3) with untrusted boundaries (T6.2)."""
    if isinstance(proposal_payload, str):
        serialized = sanitize_untrusted_text(proposal_payload)
    else:
        compact_payload = build_compact_judge_payload(
            proposal_payload,
            milestones_metadata=milestones_metadata,
        )
        serialized = json.dumps(
            sanitize_untrusted_value(compact_payload),
            ensure_ascii=False,
            default=str,
        )

    safe_level = sanitize_untrusted_text(learner_level) or "UNSPECIFIED"
    safe_context = (
        format_untrusted_block(UntrustedBlockKind.USER_INPUT, context_block, multiline=True)
        if context_block.strip()
        else ""
    )
    safe_milestones = (
        format_untrusted_block(
            UntrustedBlockKind.MILESTONE_DATA, milestones_summary, multiline=True
        )
        if milestones_summary.strip()
        else ""
    )
    parts = [
        f"[SKILL: {PEDAGOGICAL_JUDGE_SKILL.skill_id}@v{PEDAGOGICAL_JUDGE_SKILL.version}]",
        f"learner_level: {safe_level}",
    ]
    if safe_context:
        parts.append(safe_context)
    if safe_milestones:
        parts.append(safe_milestones)
    parts.append(
        "Yêu cầu hành động: Thẩm định bản đề xuất dưới đây theo rubric neo mốc 0/40/60/80/100; "
        "mọi `issue` phải dẫn rõ `evidence` và `task_ref` tồn tại trong proposal:"
    )
    parts.append(f"[PROPOSAL_PAYLOAD]\n{serialized}")
    return "\n".join(parts).strip()


def build_planning_prompt_registry() -> PromptRegistry:
    """Register all versioned planning prompt templates with canonical checksums and schemas."""
    verify_skill_stage_tool_authority()
    registry = PromptRegistry()

    core_specs: tuple[tuple[str, SkillDefinition, str, dict[str, Any]], ...] = (
        (
            GOAL_CLARIFIER_SKILL.skill_id,
            GOAL_CLARIFIER_SKILL,
            WorkflowType.PLAN_CREATION.value,
            ClarificationQuestionsLLMOutput.model_json_schema(),
        ),
        (
            MILESTONE_PLANNER_SKILL.skill_id,
            MILESTONE_PLANNER_SKILL,
            WorkflowType.PLAN_CREATION.value,
            MilestoneGenerationLLMOutput.model_json_schema(),
        ),
        (
            TASK_DECOMPOSER_SKILL.skill_id,
            TASK_DECOMPOSER_SKILL,
            WorkflowType.SCHEDULE_GENERATION.value,
            TaskProposalLLMOutput.model_json_schema(),
        ),
        (
            PEDAGOGICAL_JUDGE_SKILL.skill_id,
            PEDAGOGICAL_JUDGE_SKILL,
            WorkflowType.SCHEDULE_GENERATION.value,
            PedagogicalJudgeLLMOutput.model_json_schema(),
        ),
    )
    for prompt_id, skill, workflow_type, output_schema in core_specs:
        checksum = PromptRegistry.checksum_for(
            prompt_id=prompt_id,
            version=skill.version,
            workflow_type=workflow_type,
            skill_id=skill.skill_id,
            system_template=skill.system_instruction,
            output_schema=output_schema,
        )
        registry.register(
            PromptTemplate(
                prompt_id=prompt_id,
                version=skill.version,
                workflow_type=workflow_type,
                skill_id=skill.skill_id,
                system_template=skill.system_instruction,
                output_schema=output_schema,
                checksum=checksum,
            )
        )

    for aux in AUXILIARY_PLANNING_PROMPTS.values():
        aux_schema = aux.output_model.model_json_schema()
        checksum = PromptRegistry.checksum_for(
            prompt_id=aux.prompt_id,
            version=aux.version,
            workflow_type=aux.workflow_type,
            skill_id=aux.skill_id,
            system_template=aux.system_instruction,
            output_schema=aux_schema,
        )
        registry.register(
            PromptTemplate(
                prompt_id=aux.prompt_id,
                version=aux.version,
                workflow_type=aux.workflow_type,
                skill_id=aux.skill_id,
                system_template=aux.system_instruction,
                output_schema=aux_schema,
                checksum=checksum,
            )
        )
    return registry
