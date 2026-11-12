import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from src.planning.application.services.knowledge_tool_dispatcher import (
    RoadmapPipelineStage,
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


GOAL_CLARIFIER_SKILL = SkillDefinition(
    skill_id="goal-clarifier",
    version="1.0.0",
    title="Chuyên gia Chẩn đoán & Làm rõ Mục tiêu Học tập (SRL Forethought)",
    stage=RoadmapPipelineStage.GOAL_CLARIFICATION,
    allowed_tools=(),
    thinking_level="MEDIUM",
    max_tool_calls=0,
    system_instruction=(
        "[SKILL: goal-clarifier@v1.0.0]\n"
        "Bạn là Chuyên gia Chẩn đoán Mục tiêu Học tập của FocusFlow theo mô hình SRL Zimmerman.\n"
        "Nhiệm vụ: Phân tích [USER_PROVIDED_FACTS] và [AI_ASSUMPTIONS_AND_UNKNOWNS] để sinh ĐÚNG 2 đến 3 câu hỏi "
        "ngắn gọn bằng tiếng Việt nhằm làm rõ khoảng trống thông tin quan trọng nhất trước khi lập lộ trình.\n"
        "Quy tắc bắt buộc:\n"
        "1. KẾT HỢP TRẮC NGHIỆM VÀ TỰ LUẬN NGẮN (BẮT BUỘC):\n"
        '   - Ít nhất 1-2 câu hỏi là TRẮC NGHIỆM (`question_type: "single_choice"`): BẮT BUỘC có mảng `options` gồm 3 đến 4 phương án lựa chọn thực tế, ngắn gọn (dưới 15 từ/phương án) để người học chọn nhanh bằng 1 click (ví dụ: mức độ kiến thức nền tảng, phong cách học tập, độ sâu công nghệ).\n'
        '   - 1 câu hỏi là TỰ LUẬN NGẮN (`question_type: "text"`, `options: []`): để người học tự do nhập mục tiêu cụ thể, sản phẩm đầu ra mong muốn hoặc dự án cụ thể.\n'
        "2. NỘI DUNG VÀ THUỘC TÍNH BẮT BUỘC:\n"
        "   - Cả trường `question` và `text` BẮT BUỘC phải chứa nội dung câu hỏi rõ ràng bằng tiếng Việt (tuyệt đối không để chuỗi rỗng).\n"
        "   - Mỗi câu hỏi bắt buộc có đầy đủ: `id` (q1, q2, q3), `question_id`, `question`, `text`, `question_type`, `options`, `placeholder`, `question_purpose`, `expected_answer_format`, `diagnostic_dimension`.\n"
        "3. KHÔNG hỏi lại thông tin người học đã cung cấp trong [USER_PROVIDED_FACTS] hoặc nằm trong known_diagnostic_dimensions.\n"
        "4. KHÔNG gọi bất kỳ công cụ (tool) nào ở bước này và KHÔNG xuất suy luận nội bộ (chain-of-thought) ra ngoài JSON."
    ),
)

MILESTONE_PLANNER_SKILL = SkillDefinition(
    skill_id="learning-milestone-planner",
    version="1.0.0",
    title="Kiến trúc sư Lộ trình Cột mốc Học thuật (SRL Forethought)",
    stage=RoadmapPipelineStage.MILESTONE_PLANNING,
    allowed_tools=("search_learning_concepts", "get_concept_prerequisite_graph"),
    thinking_level="MEDIUM",
    max_tool_calls=4,
    system_instruction=(
        "[SKILL: learning-milestone-planner@v1.0.0]\n"
        "Bạn là Kiến trúc sư Lộ trình Học tập Thích ứng của FocusFlow.\n"
        "Nhiệm vụ: Thiết kế chuỗi cột mốc kiến thức tuần tự (Milestones) bằng tiếng Việt bám sát [USER_PROVIDED_FACTS], "
        "[SYSTEM_DERIVED_FACTS], [KNOWLEDGE_BASE_EVIDENCE] và [AI_ASSUMPTIONS_AND_UNKNOWNS].\n"
        "Quy tắc bắt buộc:\n"
        "1. Ưu tiên sử dụng khái niệm đã xác thực (VERIFIED) từ Knowledge Base trong `required_concepts`.\n"
        "2. Mọi khái niệm chuyên môn cần thiết nhưng không có trong Knowledge Base phải liệt kê rõ trong `unverified_concepts`.\n"
        "3. Tuân thủ nghiêm ngặt thứ tự tiên quyết từ cơ bản đến nâng cao; mỗi cột mốc có `learning_outcomes`, `completion_criteria`, `estimated_effort_minutes`.\n"
        "4. KHÔNG xuất suy luận nội bộ (chain-of-thought); chỉ trả về JSON hợp lệ theo schema."
    ),
)

TASK_DECOMPOSER_SKILL = SkillDefinition(
    skill_id="learning-task-decomposer",
    version="1.0.0",
    title="Chuyên gia Phân rã Nhiệm vụ Học tập Nguyên tử (SRL Performance Prep)",
    stage=RoadmapPipelineStage.TASK_DECOMPOSITION,
    allowed_tools=(
        "search_learning_concepts",
        "get_concept_prerequisite_graph",
        "get_learning_resources_and_guidance",
    ),
    thinking_level="MEDIUM",
    max_tool_calls=4,
    system_instruction=(
        "[SKILL: learning-task-decomposer@v1.0.0]\n"
        "Bạn là Chuyên gia Phân rã Nhiệm vụ Học tập của FocusFlow.\n"
        "Nhiệm vụ: Phân rã các cột mốc đã duyệt (`APPROVED`) thành danh sách nhiệm vụ nguyên tử (`tasks`) và đồ thị phụ thuộc (`dependencies`).\n"
        "Quy tắc bắt buộc:\n"
        "1. Mỗi nhiệm vụ có thời lượng `30 <= estimated_minutes <= 120` (tôn trọng `opt_session_minutes` và `estimation_bias_beta`).\n"
        "2. Cân bằng sư phạm giữa lý thuyết (`THEORY`), thực hành (`PRACTICE`), ôn tập (`REVIEW`) và dự án (`PROJECT`). Gán đúng `task_type` cho từng nhiệm vụ.\n"
        "3. Mỗi nhiệm vụ có `learning_objective` và `completion_criteria` đo lường được bằng tiếng Việt.\n"
        "4. Sử dụng công cụ `get_learning_resources_and_guidance` để tra cứu và đính kèm danh sách `learning_resources` (mỗi mục gồm `title`, `url`, `type`: DOCS|TUTORIAL|VIDEO|BOOK|PRACTICE, `description`) và chỉ dẫn sư phạm cho từng nhiệm vụ.\n"
        "5. Đồ thị `dependencies` (`predecessor_id -> successor_id`) phải là DAG không chu trình, không ngược thứ tự tiên quyết.\n"
        "6. KHÔNG sinh scheduled_date, scheduled_start hoặc scheduled_end. Bộ lập lịch tất định sẽ phân bổ thời gian sau khi nhận Roadmap."
    ),
)

PEDAGOGICAL_JUDGE_SKILL = SkillDefinition(
    skill_id="pedagogical-quality-judge",
    version="1.0.0",
    title="Giám khảo Thẩm định Sư phạm Tầng 3 (Tier 3 Pedagogical Judge)",
    stage=RoadmapPipelineStage.PEDAGOGICAL_JUDGE,
    allowed_tools=(),
    thinking_level="MEDIUM",
    max_tool_calls=0,
    system_instruction=(
        "[SKILL: pedagogical-quality-judge@v1.0.0]\n"
        "Bạn là Giám khảo Thẩm định Chất lượng Sư phạm độc lập (Tier 3) của FocusFlow.\n"
        "Nhiệm vụ: Đánh giá bản đề xuất lịch học (`ScheduleProposal`) về:\n"
        "1. Thứ tự tiên quyết kiến thức (không đảo ngược bài nâng cao trước bài cơ bản).\n"
        "2. Phân bổ tải nhận thức (Cognitive Load) và xen kẽ Lý thuyết - Thực hành - Ôn tập.\n"
        "3. Tính cụ thể, đo lường được của mục tiêu và tiêu chí hoàn thành.\n"
        "Quy tắc bắt buộc: Không gọi bất kỳ công cụ nào; trả về JSON gồm `overall_status` ('PASS' | 'WARN' | 'FAIL'), "
        "`pedagogical_score` (0..100), `score` (0.0..1.0), `issues`, `warnings` và `advisory_warnings` bằng tiếng Việt."
    ),
)

ROADMAP_SKILL_REGISTRY: dict[str, SkillDefinition] = {
    GOAL_CLARIFIER_SKILL.skill_id: GOAL_CLARIFIER_SKILL,
    MILESTONE_PLANNER_SKILL.skill_id: MILESTONE_PLANNER_SKILL,
    TASK_DECOMPOSER_SKILL.skill_id: TASK_DECOMPOSER_SKILL,
    PEDAGOGICAL_JUDGE_SKILL.skill_id: PEDAGOGICAL_JUDGE_SKILL,
}


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
) -> str:
    """Build user prompt for the `goal-clarifier` skill (2-3 non-redundant diagnostic questions)."""
    extra_facts: list[str] = []
    if goal_title and "[USER_PROVIDED_FACTS]" not in context_block:
        extra_facts.append(f"goal_title: {goal_title}")
    if raw_description and "[USER_PROVIDED_FACTS]" not in context_block:
        extra_facts.append(f"raw_description: {raw_description}")
    if prior_knowledge_level and "[USER_PROVIDED_FACTS]" not in context_block:
        extra_facts.append(f"prior_knowledge_level: {prior_knowledge_level}")
    if target_date_iso and "[USER_PROVIDED_FACTS]" not in context_block:
        extra_facts.append(f"target_date: {target_date_iso}")
    if known_dimensions:
        extra_facts.append(f"known_dimensions_do_not_repeat: {', '.join(known_dimensions)}")

    extra_block = "\n".join(extra_facts)
    return (
        f"[SKILL: {GOAL_CLARIFIER_SKILL.skill_id}@v{GOAL_CLARIFIER_SKILL.version}]\n"
        "Hãy tạo từ 2 đến 3 câu hỏi khảo sát ngắn gọn bằng tiếng Việt để làm rõ mục tiêu học tập.\n"
        "YÊU CẦU BẮT BUỘC:\n"
        "- Kết hợp cả câu hỏi trắc nghiệm và tự luận: Ít nhất 1-2 câu trắc nghiệm (question_type='single_choice' với mảng options 3-4 phương án cụ thể, ngắn gọn để chọn nhanh 1-click) và 1 câu tự luận ngắn (question_type='text', options=[]).\n"
        "- Cả 'question' và 'text' bắt buộc có nội dung câu hỏi rõ ràng (không để rỗng).\n"
        "- Không hỏi lại các chiều thông tin đã biết.\n"
        f"{extra_block}\n"
        f"{context_block}".strip()
    )


def build_milestone_planner_prompt(
    context_block: str = "",
    *,
    goal_title: str = "",
    raw_description: str = "",
    prior_knowledge_level: str = "BEGINNER",
    clarification_summary: str = "",
) -> str:
    """Build user prompt for the `learning-milestone-planner` skill."""
    extra_lines: list[str] = []
    if goal_title and "[USER_PROVIDED_FACTS]" not in context_block:
        extra_lines.append(f"goal_title: {goal_title}")
    if raw_description and "[USER_PROVIDED_FACTS]" not in context_block:
        extra_lines.append(f"raw_description: {raw_description}")
    if prior_knowledge_level and "[USER_PROVIDED_FACTS]" not in context_block:
        extra_lines.append(f"prior_knowledge_level: {prior_knowledge_level}")
    if clarification_summary and "[USER_PROVIDED_FACTS]" not in context_block:
        extra_lines.append(f"clarification_summary: {clarification_summary}")

    extra_block = "\n".join(extra_lines)
    return (
        f"[SKILL: {MILESTONE_PLANNER_SKILL.skill_id}@v{MILESTONE_PLANNER_SKILL.version}]\n"
        "Hãy thiết kế danh sách cột mốc (milestones) có thứ tự sequence_order liên tục bắt đầu từ 1.\n"
        "Mỗi cột mốc cần có title, description, learning_outcomes, completion_criteria, "
        "estimated_effort_minutes, required_concepts (từ VERIFIED Knowledge Base) và unverified_concepts (nếu ngoài KB).\n"
        f"{extra_block}\n"
        f"{context_block}".strip()
    )


def build_task_decomposer_prompt(
    context_block: str = "",
    *,
    milestones_summary: str = "",
    availability_summary: str = "",
) -> str:
    """Build user prompt for the `learning-task-decomposer` skill."""
    extra_lines: list[str] = []
    if milestones_summary and "approved_milestones" not in context_block:
        extra_lines.append(f"approved_milestones: {milestones_summary}")
    if availability_summary and "availability_constraints" not in context_block:
        extra_lines.append(f"availability_constraints: {availability_summary}")

    extra_block = "\n".join(extra_lines)
    return (
        f"[SKILL: {TASK_DECOMPOSER_SKILL.skill_id}@v{TASK_DECOMPOSER_SKILL.version}]\n"
        "Hãy phân rã các cột mốc đã duyệt thành danh sách nhiệm vụ học tập nguyên tử (`tasks`) "
        "(mỗi nhiệm vụ 30..120 phút, gắn đúng milestone_id của cột mốc APPROVED, kèm task_type, "
        "learning_objective, completion_criteria và danh sách learning_resources tra cứu từ Knowledge Base) "
        "và danh sách cạnh phụ thuộc (`dependencies`).\n"
        "Chỉ sinh nội dung học tập và estimated_minutes; không gán ngày hoặc giờ học.\n"
        "Đảm bảo cân bằng giữa lý thuyết (THEORY), thực hành (PRACTICE), ôn tập (REVIEW) và dự án (PROJECT).\n"
        f"{extra_block}\n"
        f"{context_block}".strip()
    )


def build_pedagogical_judge_prompt(
    proposal_payload: dict[str, Any] | str,
    *,
    context_block: str = "",
    milestones_summary: str = "",
) -> str:
    """Build user prompt for the `pedagogical-quality-judge` (Tier 3) skill."""
    serialized = (
        proposal_payload
        if isinstance(proposal_payload, str)
        else json.dumps(proposal_payload, ensure_ascii=False)
    )
    return (
        f"[SKILL: {PEDAGOGICAL_JUDGE_SKILL.skill_id}@v{PEDAGOGICAL_JUDGE_SKILL.version}]\n"
        "Hãy thẩm định chất lượng sư phạm của bản đề xuất lịch trình dưới đây (kiểm tra thứ tự tiên quyết, "
        "xen kẽ lý thuyết-thực hành, tải nhận thức và độ rõ ràng của tiêu chí hoàn thành):\n"
        f"{context_block}\n"
        f"{milestones_summary}\n"
        f"[PROPOSAL_PAYLOAD]\n{serialized}".strip()
    )


def build_task_repair_prompt(
    base_prompt: str,
    *,
    failed_attempt_number: int,
    violations: Sequence[Any],
    previous_proposal: dict[str, Any] | None = None,
) -> str:
    """Build targeted self-correction retry prompt preserving `[SELF-CORRECTION RETRY ATTEMPT #N]`."""
    violation_lines: list[str] = []
    for v in violations:
        if isinstance(v, dict):
            tier = v.get("tier", "TIER_1_OR_2")
            rule_code = v.get("rule_code", "UNKNOWN_RULE")
            message = v.get("message", "")
            details = v.get("details", {})
        else:
            tier_obj = getattr(v, "tier", "TIER_1_OR_2")
            tier = getattr(tier_obj, "value", str(tier_obj))
            rule_code = getattr(v, "rule_code", "UNKNOWN_RULE")
            message = getattr(v, "message", "")
            details = getattr(v, "details", {})
        violation_lines.append(
            f"- [{tier}] {rule_code}: {message} (details={json.dumps(details, ensure_ascii=False)})"
        )

    feedback_block = "\n".join(violation_lines)
    prev_summary = ""
    if previous_proposal and isinstance(previous_proposal.get("tasks"), list):
        prev_summary = f"\nSố lượng tasks ở lần thử trước: {len(previous_proposal['tasks'])}."

    return (
        f"{base_prompt}\n\n"
        f"[SELF-CORRECTION RETRY ATTEMPT #{failed_attempt_number}]\n"
        f"[SKILL: {TASK_DECOMPOSER_SKILL.skill_id}@v{TASK_DECOMPOSER_SKILL.version}]\n"
        "Bản đề xuất JSON ở lần thử trước đã vi phạm các ràng buộc bắt buộc (Hard Constraints) của cổng kiểm duyệt.\n"
        "Chỉ sửa các phần tử vi phạm dưới đây và giữ nguyên cấu trúc hợp lệ khác:\n"
        f"{feedback_block}"
        f"{prev_summary}\n"
        "Hãy điều chỉnh lại `tasks` và `dependencies` để khắc phục TRIỆT ĐỂ mọi mã lỗi trên và trả về JSON hợp lệ."
    )
