import json
import re
from collections.abc import AsyncIterator
from datetime import date, timedelta
from typing import Any
from uuid import NAMESPACE_DNS, uuid5

from pydantic import BaseModel

from src.shared_kernel.application.llm_port import (
    LLMProviderPort,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
)
from src.shared_kernel.config import get_settings

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_MILESTONE_ID_JSON_RE = re.compile(
    r'"milestone_id"\s*:\s*"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"'
)
_DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_SLOT_RE = re.compile(
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*:\s*(\d{2}:\d{2})-(\d{2}:\d{2})",
    re.IGNORECASE,
)
_GOAL_TITLE_TAG_RE = re.compile(r"<goal_title>\s*(.*?)\s*</goal_title>", re.DOTALL | re.IGNORECASE)

_WEEKDAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _normalize_schema_and_validate(
    raw_data: dict[str, Any],
    response_schema: dict[str, Any] | type[Any] | None,
) -> dict[str, Any]:
    """Validate raw_data with Pydantic BaseModel if response_schema is a BaseModel subclass."""
    if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
        validated = response_schema.model_validate(raw_data)
        return validated.model_dump(mode="json")
    return raw_data


def _extract_json_schema(
    response_schema: dict[str, Any] | type[Any] | None,
) -> dict[str, Any]:
    if response_schema is None:
        return {}
    if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
        return response_schema.model_json_schema()
    if isinstance(response_schema, dict):
        return response_schema
    return {}


def _extract_search_query_from_prompt(text: str) -> str:
    match = _GOAL_TITLE_TAG_RE.search(text)
    if match and match.group(1).strip():
        return match.group(1).strip()[:120]
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("goal_title:") or stripped.lower().startswith("mục tiêu:"):
            val = stripped.split(":", 1)[1].strip()
            if val:
                return val[:120]
    lower = text.lower()
    for kw in (
        "fastapi",
        "python",
        "dsa",
        "thuật toán",
        "angular",
        "typescript",
        "sql",
        "system design",
        "machine learning",
    ):
        if kw in lower:
            return kw
    return "python fastapi"


def _extract_known_dimensions_from_prompt(text: str) -> set[str]:
    known: set[str] = set()
    for dim in (
        "TIMELINE_URGENCY",
        "PRIOR_EXPOSURE",
        "TARGET_OUTCOME",
        "TIME_COMMITMENT",
        "LEARNING_STYLE",
        "TECH_STACK_DEPTH",
    ):
        if dim in text:
            known.add(dim)
    return known


def _build_mock_tasks_from_prompt(
    text: str,
    discovered_concept_ids: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Synthesize realistic, constraint-compliant study tasks from prompt context in offline mode."""
    explicit_mids = list(dict.fromkeys(_MILESTONE_ID_JSON_RE.findall(text)))
    if not explicit_mids and "MILESTONE_IDS:" in text:
        after_marker = text.split("MILESTONE_IDS:", 1)[1]
        explicit_mids = list(dict.fromkeys(_UUID_RE.findall(after_marker)))
    found_uuids = explicit_mids or list(dict.fromkeys(_UUID_RE.findall(text)))
    milestone_ids = (
        found_uuids[:5]
        if found_uuids
        else [str(uuid5(NAMESPACE_DNS, f"ms-{i}")) for i in range(1, 4)]
    )

    found_dates = _DATE_RE.findall(text)
    base_date = date(2026, 11, 2)
    if found_dates:
        try:
            base_date = date.fromisoformat(found_dates[0])
        except ValueError:
            base_date = date(2026, 11, 2)

    slot_matches = _SLOT_RE.findall(text)
    slots_by_day: dict[str, tuple[str, str]] = {}
    for d_name, s_time, e_time in slot_matches:
        d_key = d_name.lower()
        if d_key not in slots_by_day:
            slots_by_day[d_key] = (s_time, e_time)

    task_types = ("THEORY", "PRACTICE", "REVIEW")
    concept_pool = discovered_concept_ids or ["py-syntax-variables", "fastapi-routing-pydantic"]

    tasks: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []
    day_offset = 0

    for idx, mid in enumerate(milestone_ids):
        chosen_date = base_date + timedelta(days=day_offset)
        if slots_by_day:
            for step in range(14):
                candidate = base_date + timedelta(days=day_offset + step)
                wname = _WEEKDAY_NAMES[candidate.weekday()]
                if wname in slots_by_day:
                    chosen_date = candidate
                    day_offset = day_offset + step
                    break

        wname = _WEEKDAY_NAMES[chosen_date.weekday()]
        start_hhmm = "19:30"
        if wname in slots_by_day:
            start_hhmm = slots_by_day[wname][0]
        elif wname in ("saturday", "sunday"):
            start_hhmm = "14:00"

        sh, sm = (int(x) for x in start_hhmm.split(":"))
        duration_mins = 60
        total_end_m = sh * 60 + sm + duration_mins
        end_date = chosen_date + timedelta(days=total_end_m // 1440)
        eh = (total_end_m % 1440) // 60
        em = total_end_m % 60

        task_id = str(uuid5(NAMESPACE_DNS, f"mock-task-{mid}-{idx}"))
        t_type = task_types[idx % len(task_types)]
        assigned_concept = (
            concept_pool[idx % len(concept_pool)] if concept_pool else "py-syntax-variables"
        )

        tasks.append(
            {
                "task_id": task_id,
                "milestone_id": mid,
                "title": f"Phiên tự học chuyên sâu #{idx + 1} ({t_type})",
                "description": (
                    f"Thực hành và ghi chú chủ động cho cột mốc #{idx + 1} "
                    f"theo chu trình Zimmerman SRL ({t_type})."
                ),
                "task_type": t_type,
                "learning_objective": (
                    f"Nắm vững kiến thức cốt lõi và vận dụng được nội dung cột mốc #{idx + 1}"
                ),
                "completion_criteria": (
                    f"Hoàn thành bài tập kiểm tra cột mốc #{idx + 1} và ghi chú tổng kết"
                ),
                "concept_ids": [assigned_concept],
                "estimated_minutes": duration_mins,
                "scheduled_date": chosen_date.isoformat(),
                "scheduled_start": f"{chosen_date.isoformat()}T{sh:02d}:{sm:02d}:00+00:00",
                "scheduled_end": f"{end_date.isoformat()}T{eh:02d}:{em:02d}:00+00:00",
            }
        )
        if idx > 0:
            dependencies.append(
                {
                    "predecessor_id": tasks[idx - 1]["task_id"],
                    "successor_id": task_id,
                    "is_mandatory": True,
                }
            )
        day_offset += 1

    return tasks, dependencies


def _evaluate_pedagogical_quality_in_mock(effective_prompt: str) -> dict[str, Any]:
    """Deterministic pedagogical evaluation for Tier 3 Judge in offline/mock mode."""
    warnings: list[str] = []
    issues: list[dict[str, Any]] = []

    if "[PROPOSAL_PAYLOAD]" in effective_prompt:
        raw_json_part = effective_prompt.split("[PROPOSAL_PAYLOAD]", 1)[1].strip()
        try:
            payload = json.loads(raw_json_part)
            tasks = payload.get("tasks", [])
            if isinstance(tasks, list) and len(tasks) >= 2:
                # 1. Detect inverted prerequisite order by title keywords or date order
                advanced_keywords = (
                    "nâng cao",
                    "advanced",
                    "quy hoạch động",
                    "dynamic programming",
                    "outbox",
                    "distributed",
                )
                basic_keywords = (
                    "cơ bản",
                    "basic",
                    "nhập môn",
                    "beginner",
                    "biến",
                    "cú pháp",
                    "mảng",
                )

                first_adv_date: str | None = None
                last_basic_date: str | None = None
                first_adv_idx: int | None = None
                last_basic_idx: int | None = None

                task_types_seen: list[str] = []
                daily_minutes: dict[str, int] = {}

                for idx, t in enumerate(tasks):
                    if not isinstance(t, dict):
                        continue
                    title_l = str(t.get("title", "")).lower()
                    s_date = str(t.get("scheduled_date", ""))
                    est_min = int(t.get("estimated_minutes", 60) or 60)
                    t_type = str(t.get("task_type", "")).upper()
                    if t_type:
                        task_types_seen.append(t_type)
                    if s_date:
                        daily_minutes[s_date] = daily_minutes.get(s_date, 0) + est_min

                    if any(ak in title_l for ak in advanced_keywords):
                        if first_adv_idx is None:
                            first_adv_idx = idx
                        if s_date and (first_adv_date is None or s_date < first_adv_date):
                            first_adv_date = s_date
                    if any(bk in title_l for bk in basic_keywords):
                        last_basic_idx = idx
                        if s_date and (last_basic_date is None or s_date > last_basic_date):
                            last_basic_date = s_date

                if (
                    first_adv_date is not None
                    and last_basic_date is not None
                    and first_adv_date < last_basic_date
                ) or (
                    first_adv_idx is not None
                    and last_basic_idx is not None
                    and first_adv_idx < last_basic_idx
                ):
                    msg = (
                        "Cảnh báo thứ tự tiên quyết (PREREQUISITE_ORDER): Nhiệm vụ nâng cao được xếp trước "
                        "nhiệm vụ nền tảng cơ bản; nên hoàn thành kiến thức nền tảng trước."
                    )
                    warnings.append(msg)
                    issues.append(
                        {
                            "category": "PREREQUISITE_ORDER",
                            "severity": "WARNING",
                            "message": msg,
                        }
                    )

                if (
                    len(tasks) >= 3
                    and task_types_seen
                    and all(tt == "THEORY" for tt in task_types_seen)
                ):
                    msg = (
                        "Cảnh báo cân bằng lý thuyết-thực hành (THEORY_PRACTICE_BALANCE): Tất cả nhiệm vụ đều là "
                        "lý thuyết (THEORY), thiếu phiên thực hành (PRACTICE) và ôn tập (REVIEW)."
                    )
                    warnings.append(msg)
                    issues.append(
                        {
                            "category": "THEORY_PRACTICE_BALANCE",
                            "severity": "WARNING",
                            "message": msg,
                        }
                    )

                for d_iso, total_m in daily_minutes.items():
                    if total_m > 180:
                        msg = (
                            f"Cảnh báo tải nhận thức (COGNITIVE_LOAD): Ngày {d_iso} có tổng thời lượng {total_m} phút, "
                            "dễ gây quá tải nhận thức."
                        )
                        warnings.append(msg)
                        issues.append(
                            {
                                "category": "COGNITIVE_LOAD",
                                "severity": "WARNING",
                                "message": msg,
                            }
                        )
        except Exception:
            pass

    if warnings:
        return {
            "overall_status": "WARN",
            "pedagogical_score": 74.0,
            "score": 0.74,
            "issues": issues,
            "warnings": warnings,
            "advisory_warnings": warnings,
        }

    return {
        "overall_status": "PASS",
        "pedagogical_score": 92.0,
        "score": 0.92,
        "issues": [],
        "warnings": [],
        "advisory_warnings": [],
    }


class MockLLMAdapter(LLMProviderPort):
    """Deterministic Mock LLM Adapter for offline Thesis Defense & CI testing (ADR-006)."""

    def __init__(self, canned_responses: list[dict[str, Any]] | None = None) -> None:
        self._canned_responses = list(canned_responses) if canned_responses else []

    async def generate_structured(
        self,
        prompt: str | None = None,
        system_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        *,
        user_prompt: str | None = None,
        temperature: float = 0.2,
        tools: list[LLMToolDeclarationDTO] | None = None,
        tool_executor: LLMToolExecutor | None = None,
        max_tool_calls: int = 4,
        thinking_level: str | None = None,
    ) -> tuple[dict[str, Any], int, int]:
        _ = (temperature, thinking_level)
        effective_prompt = f"{system_prompt}\n{user_prompt or prompt or ''}"

        discovered_concepts: list[dict[str, Any]] = []
        if tools and tool_executor is not None and max_tool_calls > 0:
            allowed_names = {t.name for t in tools}
            calls_made = 0
            if "search_learning_concepts" in allowed_names and calls_made < max_tool_calls:
                query_str = _extract_search_query_from_prompt(effective_prompt)
                search_res = await tool_executor(
                    "search_learning_concepts",
                    {"query": query_str, "limit": 5},
                )
                calls_made += 1
                raw_concepts = search_res.get("concepts", [])
                if isinstance(raw_concepts, list):
                    discovered_concepts = [c for c in raw_concepts if isinstance(c, dict)]

            if (
                "get_concept_prerequisite_graph" in allowed_names
                and calls_made < max_tool_calls
                and discovered_concepts
            ):
                seed_ids = [
                    str(c["concept_id"]) for c in discovered_concepts[:5] if c.get("concept_id")
                ]
                if seed_ids:
                    await tool_executor(
                        "get_concept_prerequisite_graph",
                        {"concept_ids": seed_ids, "max_depth": 3},
                    )
                    calls_made += 1

        if self._canned_responses:
            raw_payload = self._canned_responses.pop(0)
            return _normalize_schema_and_validate(raw_payload, response_schema), 128, 256

        schema_dict = _extract_json_schema(response_schema)
        props = schema_dict.get("properties", {}) if isinstance(schema_dict, dict) else {}

        discovered_ids = [
            str(c.get("concept_id")) for c in discovered_concepts if c.get("concept_id")
        ]
        prompt_lower = effective_prompt.lower()
        unverified_candidates: list[str] = []
        for unverified_kw in ("rust", "solidity", "blockchain", "unreal engine", "quantum"):
            if unverified_kw in prompt_lower:
                unverified_candidates.append(f"unverified-{unverified_kw.replace(' ', '-')}")

        default_milestones = [
            {
                "sequence_order": 1,
                "title": "Nền tảng cốt lõi & Thiết lập môi trường",
                "description": "Nắm vững kiến thức nền tảng và chuẩn bị công cụ thực hành.",
                "learning_outcomes": [
                    "Hiểu rõ các khái niệm cơ sở và cấu trúc dữ liệu nền tảng",
                    "Thiết lập hoàn chỉnh môi trường phát triển và kiểm thử cục bộ",
                ],
                "completion_criteria": "Hoàn thành bài tập khởi động và vượt qua bộ test cơ bản",
                "estimated_effort_minutes": 180,
                "required_concepts": discovered_ids[:2]
                if discovered_ids
                else ["py-syntax-variables"],
                "unverified_concepts": unverified_candidates,
                "dependencies": [],
            },
            {
                "sequence_order": 2,
                "title": "Thực hành chuyên sâu & Xây dựng cấu trúc",
                "description": "Áp dụng lý thuyết vào các bài tập thực tiễn có kiểm soát.",
                "learning_outcomes": [
                    "Triển khai các thành phần cốt lõi theo kiến trúc phân tầng",
                    "Xử lý kiểm tra đầu vào và các trường hợp biên",
                ],
                "completion_criteria": "Xây dựng module chức năng hoạt động ổn định với độ phủ test >= 80%",
                "estimated_effort_minutes": 240,
                "required_concepts": (
                    discovered_ids[1:3]
                    if len(discovered_ids) >= 2
                    else ["py-control-flow-functions"]
                ),
                "unverified_concepts": [],
                "dependencies": [1],
            },
            {
                "sequence_order": 3,
                "title": "Tổng hợp, Kiểm thử & Đánh giá toàn diện",
                "description": "Hoàn thiện dự án thực tế và tự đánh giá theo chuẩn SRL.",
                "learning_outcomes": [
                    "Tích hợp toàn bộ luồng nghiệp vụ và tối ưu hiệu năng",
                    "Tự đánh giá tiến độ và đúc kết bài học theo mô hình Zimmerman SRL",
                ],
                "completion_criteria": "Hoàn thành dự án tổng hợp và vượt qua toàn bộ cổng kiểm duyệt",
                "estimated_effort_minutes": 240,
                "required_concepts": (
                    discovered_ids[2:4]
                    if len(discovered_ids) >= 3
                    else ["fastapi-routing-pydantic"]
                ),
                "unverified_concepts": [],
                "dependencies": [2],
            },
        ]

        mock_payload: dict[str, Any] = {
            "status": "mock_generated",
            "summary": "Deterministic SRL study plan generated in offline mode.",
            "milestones": (
                default_milestones
                if "milestones" in props
                and (props.get("milestones", {}).get("minItems", 0) > 0 or "tasks" not in props)
                else []
            ),
        }

        if "tasks" in props:
            if (
                "MILESTONE_IDS:" in effective_prompt
                or "GENERATE_PROPOSAL_TASKS" in effective_prompt
                or "approved_milestones" in effective_prompt
                or "learning-task-decomposer" in effective_prompt
            ):
                tasks, deps = _build_mock_tasks_from_prompt(
                    effective_prompt,
                    discovered_concept_ids=discovered_ids,
                )
                mock_payload["tasks"] = tasks
                mock_payload["dependencies"] = deps
            elif "tasks" not in mock_payload:
                mock_payload["tasks"] = []

        if "questions" in props:
            known_dims = _extract_known_dimensions_from_prompt(effective_prompt)
            is_pydantic_clarification = (
                isinstance(response_schema, type)
                and issubclass(response_schema, BaseModel)
                and response_schema.__name__ == "ClarificationQuestionsResponse"
            )
            if is_pydantic_clarification:
                candidate_questions = [
                    {
                        "id": "q1",
                        "question": "Bạn đã từng làm việc với những ngôn ngữ hoặc công cụ liên quan nào trước đây?",
                        "placeholder": "Chọn mức độ tiếp xúc trước đây của bạn...",
                        "question_type": "single_choice",
                        "options": [
                            "Chưa từng tiếp xúc, bắt đầu từ số 0",
                            "Đã tự học cú pháp và khái niệm cơ bản",
                            "Đã làm bài tập nhỏ hoặc mini project",
                            "Đã đi làm và có kinh nghiệm thực tế",
                        ],
                        "question_purpose": "Xác định điểm xuất phát thực tế để tránh lặp lại kiến thức đã vững.",
                        "expected_answer_format": "Chọn 1 đáp án phù hợp nhất.",
                        "diagnostic_dimension": "PRIOR_EXPOSURE",
                    },
                    {
                        "id": "q2",
                        "question": "Sản phẩm đầu ra hoặc kết quả cụ thể bạn muốn đạt được sau lộ trình này là gì?",
                        "placeholder": "VD: Tự xây dựng được REST API hoàn chỉnh hoặc vượt qua phỏng vấn...",
                        "question_type": "text",
                        "options": [],
                        "question_purpose": "Định hướng bài tập thực hành và tiêu chí hoàn thành cột mốc.",
                        "expected_answer_format": "Nêu mục tiêu đầu ra cụ thể (dự án, kỳ thi hoặc vị trí công việc).",
                        "diagnostic_dimension": "TARGET_OUTCOME",
                    },
                    {
                        "id": "q3",
                        "question": "Bạn ưu tiên phong cách học qua dự án thực hành ngay hay nắm chắc lý thuyết nền tảng trước?",
                        "placeholder": "Chọn phong cách học tập ưa thích...",
                        "question_type": "single_choice",
                        "options": [
                            "70% thực hành làm dự án nhỏ, 30% lý thuyết nền tảng",
                            "Cân bằng 50% lý thuyết cốt lõi - 50% thực hành",
                            "Nắm chắc lý thuyết chuyên sâu trước khi làm bài tập",
                        ],
                        "question_purpose": "Cân bằng tỷ lệ nhiệm vụ THEORY, PRACTICE và REVIEW khi phân rã lịch.",
                        "expected_answer_format": "Chọn 1 đáp án phù hợp nhất.",
                        "diagnostic_dimension": "LEARNING_STYLE",
                    },
                    {
                        "id": "q4",
                        "question": "Khung thời gian trong tuần bạn có sự tập trung cao nhất để giải quyết bài tập khó là khi nào?",
                        "placeholder": "Chọn khung thời gian tập trung nhất...",
                        "question_type": "single_choice",
                        "options": [
                            "Dưới 5 giờ/tuần (mỗi ngày 30-45 phút)",
                            "5 - 10 giờ/tuần (mỗi ngày 1 - 1.5 giờ)",
                            "10 - 20 giờ/tuần (tập trung học cường độ cao)",
                            "Linh hoạt dồn vào cuối tuần",
                        ],
                        "question_purpose": "Tối ưu phân bổ các nhiệm vụ tải nhận thức cao vào giờ vàng năng suất.",
                        "expected_answer_format": "Chọn 1 đáp án phù hợp nhất.",
                        "diagnostic_dimension": "TIME_COMMITMENT",
                    },
                    {
                        "id": "q5",
                        "question": "Bạn muốn đi sâu đến mức độ nào về mặt kiến trúc, kiểm thử và triển khai thực tế?",
                        "placeholder": "Chọn mức độ đào sâu kỹ thuật...",
                        "question_type": "single_choice",
                        "options": [
                            "Mức cơ bản: Hiểu cú pháp, chạy được ứng dụng mẫu",
                            "Mức chuẩn production: Unit test, clean code, Docker hóa",
                            "Mức nâng cao: Tối ưu hiệu năng, kiến trúc chuyên sâu",
                        ],
                        "question_purpose": "Xác định độ sâu kỹ thuật cho các cột mốc giai đoạn cuối.",
                        "expected_answer_format": "Chọn 1 đáp án phù hợp nhất.",
                        "diagnostic_dimension": "TECH_STACK_DEPTH",
                    },
                ]
                filtered = [
                    q for q in candidate_questions if q["diagnostic_dimension"] not in known_dims
                ]
                selected = (filtered if len(filtered) >= 2 else candidate_questions)[:3]
                # Re-index ids q1..qN cleanly
                mock_payload["questions"] = [
                    {**q, "id": f"q{idx + 1}"} for idx, q in enumerate(selected)
                ]
            else:
                mock_payload["questions"] = [
                    {
                        "question_id": "q1",
                        "text": "Bạn đã có kinh nghiệm lập trình cơ bản hoặc nền tảng liên quan chưa?",
                        "question_type": "single_choice",
                        "options": [
                            "Chưa từng học qua, bắt đầu từ con số 0",
                            "Đã biết cơ bản cú pháp và logic cơ bản",
                            "Đã từng làm dự án nhỏ thực tế",
                        ],
                    },
                    {
                        "question_id": "q2",
                        "text": "Phong cách và kỳ vọng phân bổ thời gian học tập của bạn thế nào?",
                        "question_type": "single_choice",
                        "options": [
                            "Học chuyên sâu vào cuối tuần",
                            "Học đều đặn mỗi ngày 1-2 tiếng",
                            "Linh hoạt theo tiến độ công việc",
                        ],
                    },
                    {
                        "question_id": "q3",
                        "text": "Mục tiêu cụ thể hoặc dự án cuối khóa bạn muốn hoàn thành là gì?",
                        "question_type": "text",
                        "options": [],
                    },
                ]

        if (
            ("score" in props and "advisory_warnings" in props)
            or "pedagogical_score" in props
            or "overall_status" in props
        ):
            judge_eval = _evaluate_pedagogical_quality_in_mock(effective_prompt)
            mock_payload.update(judge_eval)

        return _normalize_schema_and_validate(mock_payload, response_schema), 128, 256

    async def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        _ = (system_prompt, user_prompt, temperature)
        chunks = [
            '{"stage": "analyzing_goal", "progress": 25}',
            '{"stage": "validating_dag_and_availability", "progress": 75}',
            '{"stage": "completed", "progress": 100}',
        ]
        for chunk in chunks:
            yield chunk


class LiteLLMAdapter(LLMProviderPort):
    """Provider-agnostic LLM Adapter routing to Gemini 3.8 Flash (google-genai) or LiteLLM."""

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def model_identifier(self) -> str:
        provider = self._settings.llm_provider.lower()
        model = self._settings.llm_model
        if "/" in model:
            return model
        return f"{provider}/{model}"

    async def _generate_with_google_genai(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | type[Any] | None,
        temperature: float,
        tools: list[LLMToolDeclarationDTO] | None,
        tool_executor: LLMToolExecutor | None,
        max_tool_calls: int,
        thinking_level: str | None,
    ) -> tuple[dict[str, Any], int, int]:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self._settings.llm_api_key)
        model_name = self._settings.llm_model.split("/")[-1]
        candidate_models: list[str] = [model_name]
        for fallback in ("gemini-3.6-flash", "gemini-3.5-flash"):
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        async def _call_model(contents: Any, config: Any) -> Any:
            last_err: Exception | None = None
            for cand in candidate_models:
                try:
                    return await client.aio.models.generate_content(
                        model=cand,
                        contents=contents,
                        config=config,
                    )
                except Exception as e:
                    err_str = str(e)
                    last_err = e
                    if (
                        "503" in err_str
                        or "UNAVAILABLE" in err_str
                        or "high demand" in err_str
                        or "RESOURCE_EXHAUSTED" in err_str
                        or "429" in err_str
                        or "quota" in err_str.lower()
                    ):
                        continue
                    raise
            if last_err is not None:
                raise last_err
            raise RuntimeError("No candidate models available for Google GenAI")

        schema_dict = _extract_json_schema(response_schema)

        budget_map = {"LOW": 512, "MEDIUM": 2048, "HIGH": 4096}
        effective_level = (thinking_level or self._settings.llm_thinking_level or "MEDIUM").upper()
        thinking_budget = budget_map.get(effective_level, 2048)

        total_prompt_tokens = 0
        total_completion_tokens = 0
        tool_evidence_blocks: list[str] = []

        if tools and tool_executor is not None and max_tool_calls > 0:
            fn_decls = [
                types.FunctionDeclaration(
                    name=t.name,
                    description=t.description,
                    parameters_json_schema=t.parameters_schema,
                )
                for t in tools
            ]
            tool_cfg = types.GenerateContentConfig(
                system_instruction=system_prompt or None,
                temperature=temperature,
                tools=[types.Tool(function_declarations=fn_decls)],
                thinking_config=types.ThinkingConfig(
                    include_thoughts=False,
                    thinking_budget=thinking_budget,
                ),
            )
            contents: list[Any] = [user_prompt]
            calls_executed = 0

            while calls_executed < max_tool_calls:
                resp = await _call_model(
                    contents=contents,
                    config=tool_cfg,
                )
                usage = getattr(resp, "usage_metadata", None)
                if usage is not None:
                    total_prompt_tokens += int(getattr(usage, "prompt_token_count", 0) or 0)
                    total_completion_tokens += int(getattr(usage, "candidates_token_count", 0) or 0)

                fn_calls = getattr(resp, "function_calls", None) or []
                if not fn_calls:
                    break

                for fc in fn_calls:
                    if calls_executed >= max_tool_calls:
                        break
                    fc_name = str(getattr(fc, "name", "") or "")
                    raw_args = getattr(fc, "args", None) or {}
                    fc_args = dict(raw_args) if isinstance(raw_args, dict) else {}
                    tool_output = await tool_executor(fc_name, fc_args)
                    calls_executed += 1
                    tool_evidence_blocks.append(
                        f"[TOOL_RESULT name={fc_name}]\n"
                        f"{json.dumps(tool_output, ensure_ascii=False)}"
                    )
                break

        final_user_prompt = user_prompt
        if tool_evidence_blocks:
            final_user_prompt = f"{user_prompt}\n\n[TOOL_EXECUTION_RESULTS]\n" + "\n".join(
                tool_evidence_blocks
            )

        json_cfg = types.GenerateContentConfig(
            system_instruction=system_prompt or None,
            temperature=temperature,
            response_mime_type="application/json",
            response_json_schema=schema_dict if schema_dict else None,
            max_output_tokens=8192,
            thinking_config=types.ThinkingConfig(
                include_thoughts=False,
                thinking_budget=thinking_budget,
            ),
        )
        final_resp = await _call_model(
            contents=final_user_prompt,
            config=json_cfg,
        )
        usage = getattr(final_resp, "usage_metadata", None)
        if usage is not None:
            total_prompt_tokens += int(getattr(usage, "prompt_token_count", 0) or 0)
            total_completion_tokens += int(getattr(usage, "candidates_token_count", 0) or 0)

        raw_text = getattr(final_resp, "text", None) or "{}"
        clean_text = raw_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()
        try:
            parsed = json.loads(clean_text)
        except Exception:
            json_match = re.search(r"(\{.*\})", clean_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(1))
            else:
                raise
        validated = _normalize_schema_and_validate(parsed, response_schema)
        return validated, total_prompt_tokens, total_completion_tokens

    async def generate_structured(
        self,
        prompt: str | None = None,
        system_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        *,
        user_prompt: str | None = None,
        temperature: float = 0.2,
        tools: list[LLMToolDeclarationDTO] | None = None,
        tool_executor: LLMToolExecutor | None = None,
        max_tool_calls: int = 4,
        thinking_level: str | None = None,
    ) -> tuple[dict[str, Any], int, int]:
        effective_user_prompt = user_prompt if user_prompt is not None else (prompt or "")

        if self._settings.llm_provider.lower() in ("mock", "local_mock") or (
            self._settings.llm_api_key in ("", "mock-key", "your-api-key")
        ):
            return await MockLLMAdapter().generate_structured(
                prompt=effective_user_prompt,
                system_prompt=system_prompt,
                response_schema=response_schema,
                user_prompt=effective_user_prompt,
                temperature=temperature,
                tools=tools,
                tool_executor=tool_executor,
                max_tool_calls=max_tool_calls,
                thinking_level=thinking_level,
            )

        if self._settings.llm_provider.lower() == "gemini" and not self._settings.llm_base_url:
            return await self._generate_with_google_genai(
                system_prompt=system_prompt,
                user_prompt=effective_user_prompt,
                response_schema=response_schema,
                temperature=temperature,
                tools=tools,
                tool_executor=tool_executor,
                max_tool_calls=max_tool_calls,
                thinking_level=thinking_level,
            )

        from litellm import acompletion

        schema_dict = _extract_json_schema(response_schema)
        sys_content = system_prompt
        if schema_dict:
            sys_content = (
                f"{system_prompt}\n\nRespond strictly with JSON conforming to this schema:\n"
                f"{json.dumps(schema_dict, ensure_ascii=False)}"
            )

        response = await acompletion(
            model=self.model_identifier,
            messages=[
                {"role": "system", "content": sys_content},
                {"role": "user", "content": effective_user_prompt},
            ],
            temperature=temperature,
            api_key=self._settings.llm_api_key,
            api_base=self._settings.llm_base_url or None,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        parsed = json.loads(content)
        validated_dict = _normalize_schema_and_validate(parsed, response_schema)
        return validated_dict, prompt_tokens, completion_tokens

    async def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        if self._settings.llm_provider.lower() in ("mock", "local_mock") or (
            self._settings.llm_api_key in ("", "mock-key", "your-api-key")
        ):
            async for chunk in MockLLMAdapter().stream_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            ):
                yield chunk
            return

        from litellm import acompletion

        response = await acompletion(
            model=self.model_identifier,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            api_key=self._settings.llm_api_key,
            api_base=self._settings.llm_base_url or None,
            stream=True,
        )
        async for part in response:
            delta = part.choices[0].delta.content
            if delta:
                yield delta
