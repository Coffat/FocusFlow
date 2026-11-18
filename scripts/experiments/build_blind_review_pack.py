"""Build a deterministic blind human-review pack for the 10 A/B roadmaps in exp_09.

Reads `docs/experiments/exp_09_judge_and_quality_ab.json` (`part_3_quality_ab_low_vs_medium`),
shuffles the 10 roadmaps with a fixed RNG seed, strips all arm/model/thinking/attempt/judge
metadata, writes:
  - `docs/reports/blind-review-10-roadmaps.md`
  - `docs/experiments/blind_review_10_roadmaps_key.json`
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_JSON = (
    REPO_ROOT / "docs" / "experiments" / "exp_09_judge_and_quality_ab.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "blind-review-10-roadmaps.md"
DEFAULT_OUTPUT_KEY = (
    REPO_ROOT / "docs" / "experiments" / "blind_review_10_roadmaps_key.json"
)
DEFAULT_EXP10_JSON = (
    REPO_ROOT / "docs" / "experiments" / "exp_10_planner_tool_rounds_ab.json"
)
DEFAULT_HARD_DATASET_JSONL = (
    REPO_ROOT
    / "backend"
    / "tests"
    / "ai_evals"
    / "datasets"
    / "hard_planning_6_goals.jsonl"
)
DEFAULT_MILESTONES_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "blind-review-hard-6-milestones.md"
)
DEFAULT_MILESTONES_OUTPUT_KEY = (
    REPO_ROOT / "docs" / "experiments" / "blind_review_hard_6_milestones_key.json"
)
DEFAULT_SEED = 20261116

# Static goal metadata matching `scripts/experiments/exp_09_judge_and_quality_ab.py`
# (`_build_5_diverse_goals`) so blind reviewers see the exact input constraints
# without importing backend runtime modules or exposing arm/model metadata.
GOAL_CONSTRAINTS_BY_KEY: dict[str, dict[str, Any]] = {
    "G1_BEGINNER_PYTHON_FASTAPI": {
        "raw_description": (
            "Học Python cơ bản (biến, hàm, cấu trúc dữ liệu, type hints), Pydantic v2 "
            "và xây dựng REST API CRUD với FastAPI + kiểm thử pytest cơ bản trong 30 ngày."
        ),
        "start_date": "2026-11-17",
        "target_date": "2026-12-17",
        "opt_session_minutes": 60,
        "availability_summary": "MODE_A — Thứ 2–Thứ 6: 90 phút/ngày; Thứ 7 & CN: 120 phút/ngày",
    },
    "G2_INTERMEDIATE_SYSTEM_DESIGN_CACHE": {
        "raw_description": (
            "Nắm vững các chiến lược caching (Cache-Aside, Write-Through, Write-Behind), "
            "consistent hashing, phòng chống cache stampede/avalanche, eviction policies "
            "và triển khai cụm Redis phân tán có rate limiting trong 4 tuần."
        ),
        "start_date": "2026-11-17",
        "target_date": "2026-12-15",
        "opt_session_minutes": 60,
        "availability_summary": (
            "MODE_B — Thứ 3: 19:30–21:30 (120 phút); Thứ 5: 19:30–21:30 (120 phút); "
            "Thứ 7: 09:00–12:00 (180 phút)"
        ),
    },
    "G3_ADVANCED_RUST_ASYNC_TOKIO": {
        "raw_description": (
            "Làm chủ Future trait, Pin/Unpin, Waker, Tokio work-stealing scheduler, "
            "channels, backpressure, graceful shutdown và tối ưu lock-free concurrency "
            "cho network service hiệu năng cao trong 6 tuần."
        ),
        "start_date": "2026-11-17",
        "target_date": "2026-12-29",
        "opt_session_minutes": 90,
        "availability_summary": "MODE_A — Thứ 2–Thứ 6: 90 phút/ngày; Thứ 7 & CN: 150 phút/ngày",
    },
    "G4_BEGINNER_IELTS_WRITING": {
        "raw_description": (
            "Người mới bắt đầu luyện viết IELTS Academic mục tiêu 6.5: nắm cấu trúc câu "
            "học thuật, mô tả biểu đồ Task 1 (line, bar, table, process) và lập luận "
            "Task 2 (opinion, discussion, problem-solution) kèm tự chấm theo 4 tiêu chí."
        ),
        "start_date": "2026-11-17",
        "target_date": "2026-12-31",
        "opt_session_minutes": 60,
        "availability_summary": "MODE_A — Thứ 2–Thứ 6: 60 phút/ngày; Thứ 7 & CN: 90 phút/ngày",
    },
    "G5_INTERMEDIATE_DATA_ENG_AIRFLOW_DBT": {
        "raw_description": (
            "Xây dựng pipeline ELT hiện đại: thiết kế DAG Airflow idempotent (XCom, "
            "TaskFlow API, retry/SLA), mô hình hóa dữ liệu staging/mart với dbt "
            "(tests, snapshots, incremental models) và kiểm soát chất lượng dữ liệu."
        ),
        "start_date": "2026-11-17",
        "target_date": "2026-12-22",
        "opt_session_minutes": 60,
        "availability_summary": (
            "MODE_B — Thứ 2, Thứ 4, Thứ 6: 19:30–21:00 (90 phút); Thứ 7: 09:00–12:00 (180 phút)"
        ),
    },
}

FORBIDDEN_LEAK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("arm suffix -low", re.compile(r"(?<![A-Za-z0-9])-low\b", re.IGNORECASE)),
    ("arm suffix -medium", re.compile(r"(?<![A-Za-z0-9])-medium\b", re.IGNORECASE)),
    ("gemini model id", re.compile(r"gemini-\d", re.IGNORECASE)),
    ("model_id key", re.compile(r"\bmodel_id\b", re.IGNORECASE)),
    ("thinking_tokens", re.compile(r"\bthinking_tokens\b", re.IGNORECASE)),
    ("thinking_level", re.compile(r"\bthinking_level\b", re.IGNORECASE)),
    ("attempts_used", re.compile(r"\battempts_used\b", re.IGNORECASE)),
    ("judge_low", re.compile(r"\bjudge_low\b", re.IGNORECASE)),
    ("judge_medium", re.compile(r"\bjudge_medium\b", re.IGNORECASE)),
    ("pedagogical_score", re.compile(r"\bpedagogical_score\b", re.IGNORECASE)),
    ("arm_a/arm_b label", re.compile(r"\barm_[ab](?:_[a-z_]+)?\b", re.IGNORECASE)),
    (
        "server_prefetch label",
        re.compile(r"\b(?:server_prefetch|tool_calling)\b", re.IGNORECASE),
    ),
    (
        "wall_ms/rounds_count",
        re.compile(r"\b(?:wall_ms|rounds_count|prefetch_ms)\b", re.IGNORECASE),
    ),
)


def _format_task_schedule(
    task: dict[str, Any],
    blocks_by_task: dict[str, list[dict[str, Any]]],
) -> str:
    tid = str(task.get("task_id", ""))
    blocks = sorted(
        blocks_by_task.get(tid, []),
        key=lambda b: int(b.get("sequence_in_task", 0)),
    )
    if blocks:
        parts: list[str] = []
        for blk in blocks:
            b_date = blk.get("block_date") or ""
            b_start = str(blk.get("scheduled_start") or "")
            b_end = str(blk.get("scheduled_end") or "")
            dur = blk.get("scheduled_duration_minutes")
            if "T" in b_start and "T" in b_end:
                hm_start = b_start.split("T", 1)[1][:5]
                hm_end = b_end.split("T", 1)[1][:5]
                dur_tag = f" ({dur}p)" if dur else ""
                parts.append(f"{b_date} {hm_start}–{hm_end}{dur_tag}")
            elif b_date:
                parts.append(str(b_date))
        if parts:
            return "; ".join(parts)

    s_date = task.get("scheduled_date")
    s_start = str(task.get("scheduled_start") or "")
    s_end = str(task.get("scheduled_end") or "")
    if s_date and "T" in s_start and "T" in s_end:
        start_date = s_start.split("T", 1)[0]
        end_date = s_end.split("T", 1)[0]
        start_hm = s_start.split("T", 1)[1][:5]
        end_hm = s_end.split("T", 1)[1][:5]
        if start_date == end_date:
            return f"{start_date} {start_hm}–{end_hm}"
        return f"{start_date} {start_hm} → {end_date} {end_hm}"
    if s_date:
        return str(s_date)
    return "Chưa xếp lịch"


def _build_dependency_maps(
    dependencies: list[dict[str, Any]],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    predecessors: dict[str, list[str]] = {}
    successors: dict[str, list[str]] = {}
    for dep in dependencies:
        pred = str(dep.get("predecessor_id", "")).strip()
        succ = str(dep.get("successor_id", "")).strip()
        if not pred or not succ:
            continue
        mandatory = bool(dep.get("is_mandatory", True))
        tag = "bắt buộc" if mandatory else "khuyến nghị"
        predecessors.setdefault(succ, []).append(f"{pred} ({tag})")
        successors.setdefault(pred, []).append(f"{succ} ({tag})")
    return predecessors, successors


def _render_roadmap_section(label: str, entry: dict[str, Any]) -> str:
    goal_key = str(entry.get("goal_key", ""))
    goal_title = str(entry.get("goal_title", ""))
    learner_level = str(entry.get("learner_level", ""))
    constraints = GOAL_CONSTRAINTS_BY_KEY.get(goal_key, {})

    planner = entry.get("planner") or {}
    decomposer = entry.get("decomposer") or {}
    proposal = decomposer.get("proposal") or {}

    milestones = sorted(
        planner.get("milestones") or [],
        key=lambda m: int(m.get("sequence_order", 0)),
    )
    tasks = list(proposal.get("tasks") or [])
    dependencies = list(proposal.get("dependencies") or [])
    blocks_by_task: dict[str, list[dict[str, Any]]] = {}
    for blk in proposal.get("schedule_blocks") or []:
        tid = str(blk.get("task_id", ""))
        if tid:
            blocks_by_task.setdefault(tid, []).append(blk)
    predecessors_map, _ = _build_dependency_maps(dependencies)

    milestone_code_by_id: dict[str, str] = {}
    for m in milestones:
        mid = str(m.get("milestone_id", ""))
        seq = int(m.get("sequence_order", 0))
        if mid:
            milestone_code_by_id[mid] = f"M{seq}"

    tasks_by_milestone: dict[str, list[dict[str, Any]]] = {}
    for task in tasks:
        m_code = milestone_code_by_id.get(str(task.get("milestone_id", "")), "M?")
        tasks_by_milestone.setdefault(m_code, []).append(task)

    task_type_counts = decomposer.get("task_type_counts") or {}
    type_summary = (
        ", ".join(f"{k}: {v}" for k, v in sorted(task_type_counts.items())) or "N/A"
    )
    total_est_minutes = decomposer.get("total_estimated_minutes")
    if total_est_minutes is None:
        total_est_minutes = sum(int(t.get("estimated_minutes", 0) or 0) for t in tasks)

    lines: list[str] = []
    lines.append(f"## {label} — {goal_title}")
    lines.append("")
    lines.append("### Thông tin mục tiêu & ràng buộc đầu vào")
    lines.append("")
    lines.append(f"- **Trình độ người học:** `{learner_level}`")
    if constraints.get("raw_description"):
        lines.append(f"- **Mô tả mục tiêu:** {constraints['raw_description']}")
    if constraints.get("start_date") and constraints.get("target_date"):
        lines.append(
            f"- **Khung thời gian:** `{constraints['start_date']}` → `{constraints['target_date']}`"
        )
    if constraints.get("opt_session_minutes"):
        lines.append(
            f"- **Thời lượng phiên học tối ưu:** {constraints['opt_session_minutes']} phút"
        )
    if constraints.get("availability_summary"):
        lines.append(f"- **Quỹ thời gian rảnh:** {constraints['availability_summary']}")
    if planner.get("scope_summary"):
        lines.append(f"- **Tóm tắt phạm vi lộ trình:** {planner['scope_summary']}")
    deferred = planner.get("deferred_scope") or []
    if deferred:
        lines.append(f"- **Phạm vi hoãn lại:** {', '.join(str(x) for x in deferred)}")
    lines.append(
        f"- **Tổng quan cấu trúc:** {len(milestones)} milestones | {len(tasks)} tasks "
        f"({type_summary}) | {len(dependencies)} dependencies | "
        f"Tổng thời lượng: {total_est_minutes} phút ({total_est_minutes / 60:.1f} giờ) | "
        f"Đã xếp lịch: {proposal.get('scheduled_tasks_count', len(tasks))}/{len(tasks)} tasks"
    )
    lines.append("")

    lines.append("### Danh sách Milestones & Learning Outcomes")
    lines.append("")
    for m in milestones:
        seq = int(m.get("sequence_order", 0))
        m_code = f"M{seq}"
        effort = m.get("estimated_effort_minutes", 0)
        lines.append(f"#### {m_code}. {m.get('title', '')} ({effort} phút)")
        if m.get("description"):
            lines.append(f"- **Mô tả:** {m['description']}")
        outcomes = m.get("learning_outcomes") or []
        if outcomes:
            lines.append("- **Chuẩn đầu ra (Learning Outcomes):**")
            for lo in outcomes:
                if isinstance(lo, dict):
                    lines.append(
                        f"  - `{lo.get('id', '')}`: {lo.get('description', '')}"
                    )
                else:
                    lines.append(f"  - {lo}")
        if m.get("completion_criteria"):
            lines.append(
                f"- **Tiêu chí hoàn thành Milestone:** {m['completion_criteria']}"
            )
        req_concepts = m.get("required_concepts") or []
        unver_concepts = m.get("unverified_concepts") or []
        if req_concepts:
            lines.append(
                f"- **Khái niệm nền tảng:** {', '.join(f'`{c}`' for c in req_concepts)}"
            )
        if unver_concepts:
            lines.append(
                f"- **Khái niệm mở rộng (chưa có trong KB):** {', '.join(f'`{c}`' for c in unver_concepts)}"
            )
        lines.append("")

    lines.append("### Chi tiết Tasks & Phụ thuộc (Dependencies)")
    lines.append("")
    lines.append(
        "| Task | Milestone | Loại | Thời lượng | Lịch dự kiến | Outcomes | Tiên quyết (Predecessors) |"
    )
    lines.append("|---|---|---|---:|---|---|---|")
    for task in tasks:
        tid = str(task.get("task_id", ""))
        m_code = milestone_code_by_id.get(str(task.get("milestone_id", "")), "M?")
        ttype = str(task.get("task_type", ""))
        mins = int(task.get("estimated_minutes", 0) or 0)
        sched = _format_task_schedule(task, blocks_by_task)
        outcomes_str = (
            ", ".join(str(x) for x in (task.get("covered_outcome_ids") or [])) or "—"
        )
        preds_str = ", ".join(predecessors_map.get(tid, [])) or "Không"
        title_clean = str(task.get("title", "")).replace("|", "\\|")
        lines.append(
            f"| **{tid}**: {title_clean} | {m_code} | `{ttype}` | {mins} phút | {sched} | {outcomes_str} | {preds_str} |"
        )
    lines.append("")

    for m in milestones:
        seq = int(m.get("sequence_order", 0))
        m_code = f"M{seq}"
        m_tasks = tasks_by_milestone.get(m_code, [])
        if not m_tasks:
            continue
        lines.append(f"#### Chi tiết nội dung {m_code} ({len(m_tasks)} tasks)")
        lines.append("")
        for task in m_tasks:
            tid = str(task.get("task_id", ""))
            ttype = str(task.get("task_type", ""))
            mins = int(task.get("estimated_minutes", 0) or 0)
            preds_str = ", ".join(predecessors_map.get(tid, [])) or "Không"
            lines.append(
                f"- **{tid} — {task.get('title', '')}** (`{ttype}`, {mins} phút)"
            )
            if task.get("description"):
                lines.append(f"  - *Mô tả:* {task['description']}")
            if task.get("learning_objective"):
                lines.append(f"  - *Mục tiêu học tập:* {task['learning_objective']}")
            if task.get("completion_criteria"):
                lines.append(
                    f"  - *Tiêu chí hoàn thành:* {task['completion_criteria']}"
                )
            concepts = task.get("concept_ids") or []
            if concepts:
                lines.append(f"  - *Concepts:* {', '.join(f'`{c}`' for c in concepts)}")
            lines.append(
                f"  - *Tiên quyết:* {preds_str} | *Lịch dự kiến:* {_format_task_schedule(task, blocks_by_task)}"
            )
        lines.append("")

    unscheduled = proposal.get("unscheduled_tasks") or []
    if unscheduled:
        lines.append(
            f"- **Task chưa xếp được vào lịch:** {', '.join(str(x) for x in unscheduled)}"
        )
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def assert_no_metadata_leaks(markdown_text: str) -> None:
    """Verify the blind review Markdown does not expose arm/model/judge metadata."""
    findings: list[str] = []
    for label, pattern in FORBIDDEN_LEAK_PATTERNS:
        match = pattern.search(markdown_text)
        if match:
            findings.append(f"{label} (matched {match.group(0)!r})")
    if findings:
        raise RuntimeError(
            "Blind review pack metadata leak detected: " + "; ".join(findings)
        )


def build_blind_review_pack(
    *,
    input_path: Path = DEFAULT_INPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
    output_key_path: Path = DEFAULT_OUTPUT_KEY,
    seed: int = DEFAULT_SEED,
) -> tuple[Path, Path]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    part3 = payload.get("part_3_quality_ab_low_vs_medium")
    if not isinstance(part3, dict) or not isinstance(part3.get("roadmaps"), list):
        raise TypeError(
            f"Expected `part_3_quality_ab_low_vs_medium.roadmaps` list in {input_path}"
        )

    roadmaps: list[dict[str, Any]] = list(part3["roadmaps"])
    if len(roadmaps) != 10:
        raise ValueError(f"Expected 10 roadmaps, found {len(roadmaps)} in {input_path}")

    rng = random.Random(seed)
    shuffled = list(roadmaps)
    rng.shuffle(shuffled)

    blind_entries: list[tuple[str, dict[str, Any]]] = []
    key_mapping: dict[str, dict[str, Any]] = {}
    for idx, entry in enumerate(shuffled, start=1):
        label = f"R-{idx:02d}"
        blind_entries.append((label, entry))

        planner = entry.get("planner") or {}
        decomposer = entry.get("decomposer") or {}
        proposal = decomposer.get("proposal") or {}
        judges = entry.get("judge_evaluations") or {}
        judge_low = judges.get("judge_low") or {}
        judge_medium = judges.get("judge_medium") or {}

        model_id = decomposer.get("model_id") or planner.get("model_id")
        milestones_count = planner.get("milestones_count")
        if milestones_count is None:
            milestones_count = len(planner.get("milestones") or [])
        tasks_count = decomposer.get("tasks_count")
        if tasks_count is None:
            tasks_count = len(proposal.get("tasks") or [])

        key_mapping[label] = {
            "goal_id": entry.get("goal_key"),
            "arm": entry.get("arm"),
            "model_id": model_id,
            "attempts_used": decomposer.get("attempts_used"),
            "judge_low_score": judge_low.get("pedagogical_score"),
            "judge_medium_score": judge_medium.get("pedagogical_score"),
            "milestones_count": int(milestones_count),
            "tasks_count": int(tasks_count),
        }

    header_lines = [
        "# Blind Review Pack — Đánh giá chất lượng 10 Roadmap (A/B Blind)",
        "",
        "> **Hướng dẫn đánh giá mù (Blind Review):** Tài liệu này chứa **10 lộ trình học tập** (`R-01` đến `R-10`) tương ứng với 5 mục tiêu học tập (mỗi mục tiêu có 2 phương án độc lập đã được xáo trộn ngẫu nhiên). Mọi thông tin về arm thử nghiệm, model, thinking budget, số lần retry và điểm Judge tự động đã được ẩn hoàn toàn.",
        "",
        "## Quy tắc chấm điểm (Thang 1–5 cho mỗi tiêu chí)",
        "",
        "- **1 — Rất kém:** Sai lệch mục tiêu/ràng buộc nghiêm trọng, thiếu kiến thức cốt lõi hoặc không thể học theo.",
        "- **2 — Yếu:** Còn lỗ hổng rõ rệt về tiên quyết, nhiệm vụ mơ hồ hoặc lịch học quá tải/bất hợp lý.",
        "- **3 — Đạt yêu cầu cơ bản:** Bao phủ phần lớn mục tiêu nhưng còn điểm cần chỉnh sửa về độ chi tiết, phân bổ tải hoặc tiêu chí kiểm chứng.",
        "- **4 — Tốt:** Logic sư phạm mạch lạc, task cụ thể, lịch khả thi, tiêu chí hoàn thành rõ ràng.",
        "- **5 — Xuất sắc:** Phù hợp trình độ, tiến trình tối ưu, bài tập thực hành sắc nét, kiểm chứng được và tôn trọng chặt chẽ quỹ thời gian.",
        "",
        "### 5 Tiêu chí đánh giá",
        "",
        "1. **C1 — Độ phủ mục tiêu & phạm vi (Goal & Scope Coverage):** Milestones và tasks có bao phủ đầy đủ các yêu cầu trong mô tả mục tiêu và phù hợp trình độ đầu vào không?",
        "2. **C2 — Tính logic tiên quyết & tiến trình sư phạm (Prerequisite & Pedagogical Progression):** Thứ tự milestone/task và đồ thị dependencies có đi từ nền tảng → thực hành → tổng hợp một cách tự nhiên, không nhảy cóc không?",
        "3. **C3 — Độ cụ thể & tính hành động của task (Task Granularity & Actionability):** Tên task, mô tả và mục tiêu học tập có đủ rõ để người học bắt tay làm ngay trong một phiên học không?",
        "4. **C4 — Tính khả thi lịch học & tải nhận thức (Schedule Realism & Cognitive Load):** Thời lượng từng task, mật độ theo ngày/tuần và tổng tải có tôn trọng khung ngày + quỹ giờ rảnh mà không gây kiệt sức hoặc quá thưa không?",
        "5. **C5 — Độ rõ ràng tiêu chí hoàn thành & kiểm chứng (Completion Criteria & Measurability):** `completion_criteria` của milestone và task có đo lường/kiểm chứng được thay vì nói chung chung không?",
        "",
        "## Bảng chấm điểm (Điền điểm 1–5)",
        "",
        "| Mã Roadmap | C1: Độ phủ mục tiêu | C2: Tiến trình sư phạm | C3: Độ cụ thể task | C4: Khả thi lịch học | C5: Tiêu chí kiểm chứng | Tổng (/25) | Ghi chú / Nhận xét nổi bật |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for label, _ in blind_entries:
        header_lines.append(f"| **{label}** | | | | | | | |")
    header_lines.extend(["", "---", ""])

    body_sections = [
        _render_roadmap_section(label, entry) for label, entry in blind_entries
    ]
    full_markdown = "\n".join(header_lines + body_sections)

    assert_no_metadata_leaks(full_markdown)

    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.write_text(full_markdown, encoding="utf-8")

    key_payload = {
        "schema_version": "1.0",
        "seed": seed,
        "source_file": str(input_path.relative_to(REPO_ROOT))
        if input_path.is_relative_to(REPO_ROOT)
        else str(input_path),
        "blind_review_doc": str(output_md_path.relative_to(REPO_ROOT))
        if output_md_path.is_relative_to(REPO_ROOT)
        else str(output_md_path),
        "roadmaps_count": len(key_mapping),
        "mapping": key_mapping,
    }
    output_key_path.parent.mkdir(parents=True, exist_ok=True)
    output_key_path.write_text(
        json.dumps(key_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_md_path, output_key_path


def _summarize_availability_for_blind(avail: dict[str, Any]) -> str:
    mode = str(avail.get("mode", ""))
    slots = avail.get("availability_slots") or []
    slot_parts: list[str] = []
    for slot in slots:
        if not isinstance(slot, dict) or not slot.get("is_active", True):
            continue
        day = str(slot.get("day_of_week", ""))
        st = str(slot.get("start_time", ""))
        et = str(slot.get("end_time", ""))
        slot_parts.append(f"{day} {st}–{et}")
    disabled = (
        ", ".join(str(d) for d in (avail.get("disabled_weekdays") or [])) or "Không"
    )
    return f"{mode}: {', '.join(slot_parts)} | Ngày nghỉ: {disabled}"


def _render_hard_milestone_section(
    label: str,
    *,
    scenario_meta: dict[str, Any],
    planner_payload: dict[str, Any],
) -> str:
    goal = scenario_meta.get("goal") or {}
    goal_title = str(goal.get("title") or scenario_meta.get("scenario_id") or "")
    learner_level = str(scenario_meta.get("learner_level", "UNKNOWN"))
    milestones = sorted(
        planner_payload.get("milestones") or [],
        key=lambda m: int(m.get("sequence_order", 0)),
    )
    total_effort = sum(
        int(m.get("estimated_effort_minutes", 0) or 0) for m in milestones
    )
    lines: list[str] = [
        f"## {label} — {goal_title}",
        "",
        "### Thông tin mục tiêu & ràng buộc đầu vào",
        "",
        f"- **Trình độ người học:** `{learner_level}`",
        f"- **Mô tả mục tiêu:** {goal.get('raw_description', '')}",
        f"- **Khung thời gian:** `{scenario_meta.get('start_date', '')}` → `{scenario_meta.get('target_date', '')}`",
        f"- **Quỹ thời gian rảnh:** {_summarize_availability_for_blind(scenario_meta.get('availability') or {})}",
    ]
    if planner_payload.get("scope_summary"):
        lines.append(
            f"- **Tóm tắt phạm vi lộ trình:** {planner_payload['scope_summary']}"
        )
    deferred = planner_payload.get("deferred_scope") or []
    if deferred:
        lines.append(f"- **Phạm vi hoãn lại:** {', '.join(str(x) for x in deferred)}")
    lines.append(
        f"- **Tổng quan Milestone Plan:** {len(milestones)} milestones | "
        f"Tổng effort: {total_effort} phút ({total_effort / 60:.1f} giờ)"
    )
    lines.append("")
    lines.append("### Danh sách Milestones")
    lines.append("")
    for m in milestones:
        seq = int(m.get("sequence_order", 0))
        effort = int(m.get("estimated_effort_minutes", 0) or 0)
        deps = m.get("dependencies") or []
        deps_str = ", ".join(f"M{d}" for d in deps) if deps else "Không"
        lines.append(
            f"#### M{seq}. {m.get('title', '')} ({effort} phút | Phụ thuộc: {deps_str})"
        )
        if m.get("description"):
            lines.append(f"- **Mô tả:** {m['description']}")
        outcomes = m.get("learning_outcomes") or []
        if outcomes:
            lines.append("- **Chuẩn đầu ra (Learning Outcomes):**")
            for lo in outcomes:
                lines.append(f"  - {lo}")
        if m.get("completion_criteria"):
            lines.append(
                f"- **Tiêu chí hoàn thành Milestone:** {m['completion_criteria']}"
            )
        req = m.get("required_concepts") or []
        unver = m.get("unverified_concepts") or []
        if req:
            lines.append(
                f"- **Khái niệm đã xác minh (KB):** {', '.join(f'`{c}`' for c in req)}"
            )
        if unver:
            lines.append(
                f"- **Khái niệm bổ sung (ngoài KB):** {', '.join(f'`{c}`' for c in unver)}"
            )
        lines.append("")
    lines.extend(["---", ""])
    return "\n".join(lines)


def build_hard_milestones_blind_pack(
    *,
    exp10_path: Path = DEFAULT_EXP10_JSON,
    dataset_path: Path = DEFAULT_HARD_DATASET_JSONL,
    output_md_path: Path = DEFAULT_MILESTONES_OUTPUT_MD,
    output_key_path: Path = DEFAULT_MILESTONES_OUTPUT_KEY,
    seed: int = DEFAULT_SEED + 1,
) -> tuple[Path, Path]:
    """Build a blind human-review pack for the 6 hard goals' Milestone Planner outputs."""
    exp10 = json.loads(exp10_path.read_text(encoding="utf-8"))
    scenario_meta_by_id: dict[str, dict[str, Any]] = {}
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj = json.loads(line)
            scenario_meta_by_id[str(obj["scenario_id"])] = obj

    candidates: list[dict[str, Any]] = []
    for item in exp10.get("scenarios") or []:
        sid = str(item["scenario_id"])
        for arm_key in ("arm_a_tool_calling", "arm_b_server_prefetch"):
            arm_data = item.get(arm_key) or {}
            if arm_data.get("milestones"):
                candidates.append(
                    {
                        "scenario_id": sid,
                        "arm_key": arm_key,
                        "milestones_count": int(
                            arm_data.get(
                                "milestones_count", len(arm_data["milestones"])
                            )
                        ),
                        "planner_payload": arm_data,
                    }
                )

    rng = random.Random(seed)
    rng.shuffle(candidates)

    blind_items: list[tuple[str, dict[str, Any]]] = []
    mapping: dict[str, dict[str, Any]] = {}
    for idx, cand in enumerate(candidates, start=1):
        label = f"M-{idx:02d}"
        blind_items.append((label, cand))
        arm_data = cand["planner_payload"]
        mapping[label] = {
            "scenario_id": cand["scenario_id"],
            "arm": cand["arm_key"],
            "milestones_count": cand["milestones_count"],
            "rounds_count": arm_data.get("rounds_count"),
            "tool_calls_count": arm_data.get("tool_calls_count"),
            "wall_ms": arm_data.get("wall_ms") or arm_data.get("total_ms"),
        }

    header_lines = [
        "# Blind Review Pack — Đầu ra Milestone Planner cho 6 Mục tiêu khó (`M-01`..`M-12`)",
        "",
        f"> **Hướng dẫn đánh giá mù (Blind Review):** Tài liệu này chứa **{len(blind_items)} phương án Milestone** cho 6 mục tiêu khó (bao gồm cả các ca cho 4 milestones lẫn ≥5 milestones), đã được xáo trộn ngẫu nhiên. Mọi thông tin về arm thử nghiệm (tool-calling vs server-prefetch), số vòng gọi tool, độ trễ và model đã được ẩn hoàn toàn.",
        "",
        "## Bảng chấm điểm (Thang 1–5 cho mỗi tiêu chí)",
        "",
        "- **C1 — Độ phủ mục tiêu & phạm vi:** Có bao phủ đủ các yêu cầu kỹ thuật cốt lõi trong đề bài và phù hợp deadline/quỹ giờ không?",
        "- **C2 — Phân rã milestone & tính tiên quyết:** Số lượng milestone (kể cả ca 4 milestone) và thứ tự phụ thuộc có hợp lý, không bị gộp quá thô hoặc chẻ quá vụn không?",
        "- **C3 — Độ sâu Learning Outcomes & Verification:** Learning outcomes và `completion_criteria` có sắc nét, đo lường được với người học mục tiêu không?",
        "- **C4 — Cân đối Effort (`estimated_effort_minutes`):** Tổng thời lượng milestone có sát quỹ thời gian khả dụng đến `target_date` không?",
        "- **C5 — Mức độ sẵn sàng cho bước Task Decomposer:** Nếu giao danh sách milestone này cho Decomposer rã task, cấu trúc có đủ rõ để không thiếu/lệch phạm vi không?",
        "",
        "| Mã Plan | C1: Độ phủ mục tiêu | C2: Phân rã & Số lượng MS | C3: Outcomes & Kiểm chứng | C4: Cân đối Effort | C5: Sẵn sàng Decompose | Tổng (/25) | Ghi chú (đặc biệt các ca 4 MS) |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for label, _ in blind_items:
        header_lines.append(f"| **{label}** | | | | | | | |")
    header_lines.extend(["", "---", ""])

    sections = [
        _render_hard_milestone_section(
            label,
            scenario_meta=scenario_meta_by_id[cand["scenario_id"]],
            planner_payload=cand["planner_payload"],
        )
        for label, cand in blind_items
    ]
    full_markdown = "\n".join(header_lines + sections)
    assert_no_metadata_leaks(full_markdown)

    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.write_text(full_markdown, encoding="utf-8")

    key_payload = {
        "schema_version": "1.0",
        "seed": seed,
        "source_file": str(exp10_path.relative_to(REPO_ROOT))
        if exp10_path.is_relative_to(REPO_ROOT)
        else str(exp10_path),
        "blind_review_doc": str(output_md_path.relative_to(REPO_ROOT))
        if output_md_path.is_relative_to(REPO_ROOT)
        else str(output_md_path),
        "plans_count": len(mapping),
        "mapping": mapping,
    }
    output_key_path.parent.mkdir(parents=True, exist_ok=True)
    output_key_path.write_text(
        json.dumps(key_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_md_path, output_key_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate blind review Markdown pack(s) and sealed key JSON(s).",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--output-key", type=Path, default=DEFAULT_OUTPUT_KEY)
    parser.add_argument("--exp10-input", type=Path, default=DEFAULT_EXP10_JSON)
    parser.add_argument(
        "--milestones-md", type=Path, default=DEFAULT_MILESTONES_OUTPUT_MD
    )
    parser.add_argument(
        "--milestones-key", type=Path, default=DEFAULT_MILESTONES_OUTPUT_KEY
    )
    parser.add_argument("--include-hard-milestones", action="store_true", default=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    md_path, key_path = build_blind_review_pack(
        input_path=args.input,
        output_md_path=args.output_md,
        output_key_path=args.output_key,
        seed=args.seed,
    )
    print(f"Generated blind review Markdown: {md_path}")
    print(f"Generated sealed key JSON:     {key_path}")
    if args.include_hard_milestones and args.exp10_input.exists():
        m_md, m_key = build_hard_milestones_blind_pack(
            exp10_path=args.exp10_input,
            output_md_path=args.milestones_md,
            output_key_path=args.milestones_key,
            seed=args.seed + 1,
        )
        print(f"Generated hard milestones blind Markdown: {m_md}")
        print(f"Generated hard milestones key JSON:       {m_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
