"""Deterministic LLMProviderPort test double for pure offline unit tests."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Sequence
from datetime import date, timedelta
from typing import Any
from uuid import NAMESPACE_DNS, uuid5

from pydantic import BaseModel

from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMProviderPort,
    LLMToolCallResultDTO,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
)

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

_CANONICAL_DIMENSIONS: tuple[str, ...] = (
    "TARGET_OUTCOME",
    "PRIOR_KNOWLEDGE",
    "PRACTICAL_EXPERIENCE",
    "TIME_COMMITMENT",
    "TIMELINE",
    "DESIRED_DEPTH",
    "LEARNING_PREFERENCE",
)

_DIMENSION_ALIAS_MAP: dict[str, str] = {
    "KNOWLEDGE_BASELINE": "PRIOR_KNOWLEDGE",
    "PRIOR_EXPOSURE": "PRIOR_KNOWLEDGE",
    "TECH_STACK_DEPTH": "DESIRED_DEPTH",
    "TARGET_DEPTH": "DESIRED_DEPTH",
    "LEARNING_STYLE": "LEARNING_PREFERENCE",
    "LEARNING_CONSTRAINTS": "TIME_COMMITMENT",
    "TIME_BUDGET": "TIME_COMMITMENT",
    "TIMELINE_URGENCY": "TIMELINE",
    "DEADLINE_CONSTRAINTS": "TIMELINE",
    "PROJECT_CONTEXT": "TARGET_OUTCOME",
    "ASSESSMENT_PREFERENCE": "PRACTICAL_EXPERIENCE",
    "GENERAL": "PRIOR_KNOWLEDGE",
}


def _normalize_schema_and_validate(
    raw_data: Any,
    response_schema: dict[str, Any] | type[Any] | None,
) -> dict[str, Any]:
    if isinstance(raw_data, list):
        if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
            fields = getattr(response_schema, "model_fields", {})
            if "questions" in fields:
                raw_data = {"questions": raw_data}
            elif "milestones" in fields:
                raw_data = {"milestones": raw_data}
            elif "tasks" in fields:
                raw_data = {"tasks": raw_data, "dependencies": []}
            elif len(fields) == 1:
                single_key = next(iter(fields))
                raw_data = {single_key: raw_data}
            else:
                raw_data = {"items": raw_data}
        elif isinstance(response_schema, dict):
            props = response_schema.get("properties", {})
            if "milestones" in props:
                raw_data = {"milestones": raw_data}
            elif "tasks" in props:
                raw_data = {"tasks": raw_data, "dependencies": []}
            elif "questions" in props:
                raw_data = {"questions": raw_data}
            elif len(props) == 1:
                raw_data = {next(iter(props)): raw_data}
            else:
                raw_data = {"items": raw_data}
        else:
            raw_data = {"items": raw_data}

    if isinstance(raw_data, dict):
        raw_data = dict(raw_data)
        if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
            fields = getattr(response_schema, "model_fields", {})
            for target_field in ("questions", "milestones", "tasks"):
                if target_field in fields and target_field not in raw_data:
                    for alt in ("data", "result", "items", "list", f"{target_field}_list"):
                        if isinstance(raw_data.get(alt), list):
                            raw_data[target_field] = raw_data[alt]
                            break
            if "milestones" in fields:
                raw_data.setdefault(
                    "scope_summary",
                    str(raw_data.get("summary") or "Lộ trình cột mốc thích ứng theo mục tiêu."),
                )
                raw_data.setdefault("deferred_scope", [])
            if "score" in fields and "issues" in fields and "tasks" not in fields:
                raw_score = raw_data.get("score")
                if raw_score is None and isinstance(raw_data.get("pedagogical_score"), int | float):
                    raw_score = raw_data["pedagogical_score"]
                if isinstance(raw_score, float) and 0.0 < raw_score <= 1.0:
                    raw_data["score"] = int(round(raw_score * 100))
                elif isinstance(raw_score, int | float):
                    raw_data["score"] = int(round(float(raw_score)))
                raw_data.setdefault("issues", [])
        elif isinstance(response_schema, dict):
            props = response_schema.get("properties", {})
            for target_prop in ("questions", "milestones", "tasks"):
                if target_prop in props and target_prop not in raw_data:
                    for alt in ("data", "result", "items", "list", f"{target_prop}_list"):
                        if isinstance(raw_data.get(alt), list):
                            raw_data[target_prop] = raw_data[alt]
                            break

    if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
        validated = response_schema.model_validate(raw_data)
        return validated.model_dump(mode="json")
    return raw_data if isinstance(raw_data, dict) else {"data": raw_data}


def _extract_json_schema(response_schema: dict[str, Any] | type[Any] | None) -> dict[str, Any]:
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
    explicit_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith(
            ("known_diagnostic_dimensions:", "known_dimensions_do_not_repeat:")
        )
    ]
    search_text = (
        "\n".join(explicit_lines)
        if explicit_lines
        else text.split("[INFORMATION_GAPS_TO_CLARIFY]", 1)[0]
    )
    for dim in _CANONICAL_DIMENSIONS:
        if dim in search_text:
            known.add(dim)
    for alias, canonical in _DIMENSION_ALIAS_MAP.items():
        if alias in search_text:
            known.add(canonical)
    facts_section = text.split("[INFORMATION_GAPS_TO_CLARIFY]", 1)[0].lower()
    if any(
        marker in facts_section
        for marker in (
            "giờ/ngày",
            "giờ/tuần",
            "tiếng/ngày",
            "tiếng/tuần",
            "hours/day",
            "hours/week",
            "h/ngày",
            "h/tuần",
        )
    ):
        known.add("TIME_COMMITMENT")
    return known


def _build_stub_tasks_from_prompt(
    text: str,
    discovered_concept_ids: list[str] | None = None,
    discovered_resource_ids: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
    resource_id_pool = list(dict.fromkeys(discovered_resource_ids or []))

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

        task_id = f"T{idx + 1}"
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
                "concept_ids": list(dict.fromkeys([assigned_concept, *concept_pool])),
                "covered_outcome_ids": [
                    f"M{idx + 1}-O{outcome_index}" for outcome_index in range(1, 9)
                ],
                "resource_ids": resource_id_pool[:3],
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


def _evaluate_pedagogical_quality_stub(effective_prompt: str) -> dict[str, Any]:
    warnings: list[str] = []
    issues: list[dict[str, Any]] = []

    if "[PROPOSAL_PAYLOAD]" in effective_prompt:
        raw_json_part = effective_prompt.split("[PROPOSAL_PAYLOAD]", 1)[1].strip()
        try:
            payload = json.loads(raw_json_part)
            tasks = payload.get("tasks", [])
            if isinstance(tasks, list) and len(tasks) >= 2:
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
                    adv_task = tasks[first_adv_idx] if first_adv_idx is not None else {}
                    adv_ref = (
                        str(adv_task.get("task_id") or adv_task.get("id") or "").strip() or None
                    )
                    issues.append(
                        {
                            "category": "PREREQUISITE_ORDER",
                            "severity": "WARNING",
                            "message": msg,
                            "evidence": f"Task nâng cao '{adv_task.get('title', '')}' xuất hiện trước nhiệm vụ nền tảng.",
                            "task_ref": adv_ref,
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
                            "evidence": f"{len(task_types_seen)}/{len(tasks)} nhiệm vụ có task_type=THEORY.",
                            "task_ref": None,
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
                                "evidence": f"Tổng thời lượng ngày {d_iso} = {total_m} phút (> 180 phút).",
                                "task_ref": None,
                            }
                        )
        except Exception:
            pass

    if warnings:
        return {
            "overall_status": "WARN",
            "pedagogical_score": 74.0,
            "score": 74,
            "issues": issues,
            "warnings": warnings,
            "advisory_warnings": warnings,
        }

    return {
        "overall_status": "PASS",
        "pedagogical_score": 92.0,
        "score": 92,
        "issues": [],
        "warnings": [],
        "advisory_warnings": [],
    }


def _tool_name(tool: LLMToolDeclarationDTO | dict[str, Any]) -> str:
    if isinstance(tool, dict):
        return str(tool.get("name", ""))
    return tool.name


class StubLLMAdapter(LLMProviderPort):
    """Deterministic test double for pure offline unit tests (lives strictly under tests/helpers)."""

    def __init__(self, canned_responses: list[dict[str, Any]] | None = None) -> None:
        self._canned_responses = list(canned_responses) if canned_responses else []
        self.model_used: str = "stub-deterministic"
        self.last_model_used: str = "stub-deterministic"
        self.degraded_model_used: bool = False
        self.last_degraded_model_used: bool = False

    @property
    def supports_native_structured_output(self) -> bool:
        return True

    async def generate_structured(
        self,
        *,
        system_prompt: str = "",
        user_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        tools: Sequence[LLMToolDeclarationDTO | dict[str, Any]] | None = None,
        tool_executor: LLMToolExecutor | None = None,
        max_tool_calls: int = 2,
        thinking_level: str | None = None,
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> LLMGenerationResult:
        del thinking_level, timeout_seconds, tool_call_timeout_seconds
        effective_prompt = f"{system_prompt}\n{user_prompt}"

        discovered_concepts: list[dict[str, Any]] = []
        discovered_resources: list[dict[str, Any]] = []
        tool_records: list[LLMToolCallResultDTO] = []
        if tools and tool_executor is not None and max_tool_calls > 0:
            allowed_names = {_tool_name(t) for t in tools}
            calls_made = 0
            if "search_learning_concepts" in allowed_names and calls_made < max_tool_calls:
                query_str = _extract_search_query_from_prompt(effective_prompt)
                args_search = {"query": query_str, "limit": 5}
                search_res = await tool_executor("search_learning_concepts", args_search)
                calls_made += 1
                if isinstance(search_res, dict):
                    tool_records.append(
                        LLMToolCallResultDTO(
                            tool_name="search_learning_concepts",
                            arguments=args_search,
                            output=search_res,
                        )
                    )
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
                    args_graph = {"concept_ids": seed_ids, "max_depth": 3}
                    graph_res = await tool_executor("get_concept_prerequisite_graph", args_graph)
                    calls_made += 1
                    if isinstance(graph_res, dict):
                        tool_records.append(
                            LLMToolCallResultDTO(
                                tool_name="get_concept_prerequisite_graph",
                                arguments=args_graph,
                                output=graph_res,
                            )
                        )

            if (
                "get_learning_resources_and_guidance" in allowed_names
                and calls_made < max_tool_calls
            ):
                seed_ids = [
                    str(c["concept_id"]) for c in discovered_concepts[:5] if c.get("concept_id")
                ]
                args_res: dict[str, Any] = {
                    "query": _extract_search_query_from_prompt(effective_prompt),
                    "limit": 3,
                }
                if seed_ids:
                    args_res["concept_ids"] = seed_ids
                res_out = await tool_executor("get_learning_resources_and_guidance", args_res)
                calls_made += 1
                if isinstance(res_out, dict):
                    tool_records.append(
                        LLMToolCallResultDTO(
                            tool_name="get_learning_resources_and_guidance",
                            arguments=args_res,
                            output=res_out,
                        )
                    )
                    raw_res_list = res_out.get("resources", [])
                    if isinstance(raw_res_list, list):
                        discovered_resources = [r for r in raw_res_list if isinstance(r, dict)]

        if "[INDEPENDENT_CRITIC:" in effective_prompt:
            return LLMGenerationResult(
                payload={"status": "PASS", "score": 100, "issues": []},
                prompt_tokens=32,
                output_tokens=16,
                thinking_tokens=0,
                model_id=self.last_model_used or self.model_used,
                raw_tool_results=tuple(tool_records),
            )

        discovered_ids = [
            str(c.get("concept_id")) for c in discovered_concepts if c.get("concept_id")
        ]
        discovered_resource_ids = [
            str(r.get("resource_id")) for r in discovered_resources if r.get("resource_id")
        ]
        if self._canned_responses:
            raw_payload = self._canned_responses.pop(0)
            if isinstance(raw_payload, dict) and isinstance(raw_payload.get("tasks"), list):
                prompt_concepts = [
                    concept.strip()
                    for match in re.findall(r"required_concepts=([^|\n]+)", effective_prompt)
                    for concept in match.split(",")
                    if concept.strip()
                ]
                concept_pool = list(dict.fromkeys([*prompt_concepts, *discovered_ids])) or [
                    "py-syntax-variables",
                    "py-control-flow-functions",
                    "fastapi-routing-pydantic",
                ]
                enriched_tasks: list[dict[str, Any]] = []
                for index, raw_task in enumerate(raw_payload["tasks"]):
                    if not isinstance(raw_task, dict):
                        continue
                    enriched_tasks.append(
                        {
                            **raw_task,
                            "task_id": raw_task.get("task_id") or f"T{index + 1}",
                            "learning_objective": raw_task.get("learning_objective")
                            or f"Vận dụng được nội dung học tập của nhiệm vụ {index + 1}",
                            "completion_criteria": raw_task.get("completion_criteria")
                            or f"Hoàn thành sản phẩm và kiểm tra đầu ra của nhiệm vụ {index + 1}",
                            "concept_ids": raw_task.get("concept_ids") or concept_pool,
                            "covered_outcome_ids": raw_task.get("covered_outcome_ids")
                            or [
                                f"M{milestone_index}-O{outcome_index}"
                                for milestone_index in range(1, 9)
                                for outcome_index in range(1, 9)
                            ],
                        }
                    )
                expected_milestone_ids = list(
                    dict.fromkeys(_MILESTONE_ID_JSON_RE.findall(effective_prompt))
                )
                existing_milestone_ids = {str(task.get("milestone_id")) for task in enriched_tasks}
                for sequence_order, milestone_id in enumerate(expected_milestone_ids, start=1):
                    if milestone_id in existing_milestone_ids:
                        continue
                    enriched_tasks.append(
                        {
                            "task_id": f"T{len(enriched_tasks) + 1}",
                            "milestone_id": milestone_id,
                            "title": f"Nhiệm vụ bao phủ cột mốc {sequence_order}",
                            "description": "Học, thực hành và kiểm tra các nội dung bắt buộc.",
                            "task_type": "PRACTICE",
                            "learning_objective": "Vận dụng được toàn bộ kết quả học tập của cột mốc",
                            "completion_criteria": "Hoàn thành bài thực hành và vượt qua kiểm tra đầu ra",
                            "concept_ids": concept_pool,
                            "covered_outcome_ids": [
                                f"M{sequence_order}-O{outcome_index}"
                                for outcome_index in range(1, 9)
                            ],
                            "resource_ids": discovered_resource_ids[:3],
                            "estimated_minutes": 60,
                            "scheduled_date": "",
                        }
                    )
                raw_payload = {**raw_payload, "tasks": enriched_tasks}
            normalized_canned = _normalize_schema_and_validate(raw_payload, response_schema)
            return LLMGenerationResult(
                payload=normalized_canned,
                prompt_tokens=128,
                output_tokens=256,
                thinking_tokens=0,
                model_id=self.last_model_used or self.model_used,
                raw_tool_results=tuple(tool_records),
            )

        schema_dict = _extract_json_schema(response_schema)
        props = schema_dict.get("properties", {}) if isinstance(schema_dict, dict) else {}

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

        stub_payload: dict[str, Any] = {
            "status": "stub_generated",
            "summary": "Deterministic SRL study plan generated by unit test stub.",
            "scope_summary": "Bao phủ đầy đủ các cột mốc trọng tâm phù hợp với quỹ thời gian và trình độ hiện tại.",
            "deferred_scope": [],
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
                tasks, deps = _build_stub_tasks_from_prompt(
                    effective_prompt,
                    discovered_concept_ids=list(
                        dict.fromkeys(
                            [
                                concept.strip()
                                for match in re.findall(
                                    r"required_concepts=([^|\n]+)", effective_prompt
                                )
                                for concept in match.split(",")
                                if concept.strip()
                            ]
                            + discovered_ids
                        )
                    ),
                    discovered_resource_ids=discovered_resource_ids,
                )
                stub_payload["tasks"] = tasks
                stub_payload["dependencies"] = deps
            elif "tasks" not in stub_payload:
                stub_payload["tasks"] = []

        if "questions" in props:
            known_dims = _extract_known_dimensions_from_prompt(effective_prompt)
            schema_name = (
                response_schema.__name__
                if isinstance(response_schema, type) and issubclass(response_schema, BaseModel)
                else ""
            )
            if schema_name == "ProveQuestionsLLMOutput":
                stub_payload["questions"] = [
                    {
                        "id": "q1",
                        "prompt": "Giải thích nguyên lý cốt lõi của cột mốc bằng ví dụ thực tế của bạn.",
                    },
                    {
                        "id": "q2",
                        "prompt": "Nêu một lỗi thường gặp khi triển khai và cách phát hiện, khắc phục.",
                    },
                    {
                        "id": "q3",
                        "prompt": "Vận dụng kiến thức vừa học vào một tình huống bài toán mới.",
                    },
                ]
            elif schema_name in (
                "ClarificationQuestionsResponse",
                "ClarificationQuestionsLLMOutput",
                "ClarificationFollowupLLMOutput",
            ):
                candidate_questions = [
                    {
                        "id": "q1",
                        "question": "Bạn đã từng làm việc với những ngôn ngữ hoặc công cụ liên quan nào trước đây?",
                        "text": "Bạn đã từng làm việc với những ngôn ngữ hoặc công cụ liên quan nào trước đây?",
                        "placeholder": "Chọn mức độ tiếp xúc trước đây của bạn...",
                        "question_type": "single_choice",
                        "type": "single_choice",
                        "options": [
                            "Chưa từng tiếp xúc, bắt đầu từ số 0",
                            "Đã tự học cú pháp và khái niệm cơ bản",
                            "Đã làm bài tập nhỏ hoặc mini project",
                            "Đã đi làm và có kinh nghiệm thực tế",
                            "Khác (mô tả kinh nghiệm riêng của bạn)",
                        ],
                        "question_purpose": "Xác định điểm xuất phát thực tế để tránh lặp lại kiến thức đã vững.",
                        "purpose": "Xác định điểm xuất phát thực tế để tránh lặp lại kiến thức đã vững.",
                        "expected_answer_format": "Chọn 1 đáp án phù hợp nhất.",
                        "diagnostic_dimension": "PRIOR_KNOWLEDGE",
                    },
                    {
                        "id": "q2",
                        "question": "Sản phẩm đầu ra hoặc kết quả cụ thể bạn muốn đạt được sau lộ trình này là gì?",
                        "text": "Sản phẩm đầu ra hoặc kết quả cụ thể bạn muốn đạt được sau lộ trình này là gì?",
                        "placeholder": "VD: Tự xây dựng được REST API hoàn chỉnh hoặc vượt qua phỏng vấn...",
                        "question_type": "text",
                        "type": "text",
                        "options": [],
                        "question_purpose": "Định hướng bài tập thực hành và tiêu chí hoàn thành cột mốc.",
                        "purpose": "Định hướng bài tập thực hành và tiêu chí hoàn thành cột mốc.",
                        "expected_answer_format": "Nêu mục tiêu đầu ra cụ thể (dự án, kỳ thi hoặc vị trí công việc).",
                        "diagnostic_dimension": "TARGET_OUTCOME",
                    },
                    {
                        "id": "q3",
                        "question": "Bạn ưu tiên phong cách học qua dự án thực hành ngay hay nắm chắc lý thuyết nền tảng trước?",
                        "text": "Bạn ưu tiên phong cách học qua dự án thực hành ngay hay nắm chắc lý thuyết nền tảng trước?",
                        "placeholder": "Chọn phong cách học tập ưa thích...",
                        "question_type": "single_choice",
                        "type": "single_choice",
                        "options": [
                            "70% thực hành làm dự án nhỏ, 30% lý thuyết nền tảng",
                            "Cân bằng 50% lý thuyết cốt lõi - 50% thực hành",
                            "Nắm chắc lý thuyết chuyên sâu trước khi làm bài tập",
                            "Khác (nêu phong cách học bạn thấy hiệu quả nhất)",
                        ],
                        "question_purpose": "Cân bằng tỷ lệ nhiệm vụ THEORY, PRACTICE và REVIEW khi phân rã lịch.",
                        "purpose": "Cân bằng tỷ lệ nhiệm vụ THEORY, PRACTICE và REVIEW khi phân rã lịch.",
                        "expected_answer_format": "Chọn 1 đáp án phù hợp nhất.",
                        "diagnostic_dimension": "LEARNING_PREFERENCE",
                    },
                    {
                        "id": "q4",
                        "question": "Khung thời gian trong tuần bạn có sự tập trung cao nhất để giải quyết bài tập khó là khi nào?",
                        "text": "Khung thời gian trong tuần bạn có sự tập trung cao nhất để giải quyết bài tập khó là khi nào?",
                        "placeholder": "Chọn khung thời gian tập trung nhất...",
                        "question_type": "single_choice",
                        "type": "single_choice",
                        "options": [
                            "Dưới 5 giờ/tuần (mỗi ngày 30-45 phút)",
                            "5 - 10 giờ/tuần (mỗi ngày 1 - 1.5 giờ)",
                            "10 - 20 giờ/tuần (tập trung học cường độ cao)",
                            "Linh hoạt dồn vào cuối tuần",
                            "Khác (nêu quỹ thời gian đặc thù của bạn)",
                        ],
                        "question_purpose": "Tối ưu phân bổ các nhiệm vụ tải nhận thức cao vào giờ vàng năng suất.",
                        "purpose": "Tối ưu phân bổ các nhiệm vụ tải nhận thức cao vào giờ vàng năng suất.",
                        "expected_answer_format": "Chọn 1 đáp án phù hợp nhất.",
                        "diagnostic_dimension": "TIME_COMMITMENT",
                    },
                    {
                        "id": "q5",
                        "question": "Những mảng nội dung hoặc mức độ chuyên sâu nào bạn muốn ưu tiên rèn luyện nhiều nhất?",
                        "text": "Những mảng nội dung hoặc mức độ chuyên sâu nào bạn muốn ưu tiên rèn luyện nhiều nhất?",
                        "placeholder": "Chọn các mảng trọng tâm mong muốn...",
                        "question_type": "multiple_choice",
                        "type": "multiple_choice",
                        "options": [
                            "Kiến trúc hệ thống & tư duy thiết kế giải pháp",
                            "Thực hành viết code bài tập & dự án thực tế",
                            "Luyện đề thi chứng chỉ & kỹ thuật phỏng vấn",
                            "Tối ưu hiệu năng, bảo mật & CI/CD",
                            "Khác (bổ sung chủ đề ưu tiên khác)",
                        ],
                        "question_purpose": "Xác định các trọng tâm chuyên môn để ưu tiên số lượng bài tập và thời lượng.",
                        "purpose": "Xác định các trọng tâm chuyên môn để ưu tiên số lượng bài tập và thời lượng.",
                        "expected_answer_format": "Có thể chọn nhiều phương án phù hợp.",
                        "diagnostic_dimension": "DESIRED_DEPTH",
                    },
                    {
                        "id": "q6",
                        "question": "Bạn có mốc hạn hoàn thành hoặc lịch thi cụ thể nào cần ưu tiên trước không?",
                        "text": "Bạn có mốc hạn hoàn thành hoặc lịch thi cụ thể nào cần ưu tiên trước không?",
                        "placeholder": "Chọn mức độ khẩn cấp về thời hạn của bạn...",
                        "question_type": "single_choice",
                        "type": "single_choice",
                        "options": [
                            "Cần hoàn thành gấp trong 2 - 4 tuần tới",
                            "Mục tiêu trung hạn trong 1 - 2 tháng tới",
                            "Học nâng cao bền vững theo quý (3 tháng)",
                            "Khác (mô tả hạn chót cụ thể của bạn)",
                        ],
                        "question_purpose": "Điều chỉnh mật độ nhiệm vụ và dự phòng rủi ro quá tải lịch học.",
                        "purpose": "Điều chỉnh mật độ nhiệm vụ và dự phòng rủi ro quá tải lịch học.",
                        "expected_answer_format": "Chọn 1 đáp án phù hợp nhất.",
                        "diagnostic_dimension": "TIMELINE",
                    },
                    {
                        "id": "q7",
                        "question": "Bạn đã từng thực hành làm dự án thật hoặc xử lý tình huống thực tế tương tự chưa?",
                        "text": "Bạn đã từng thực hành làm dự án thật hoặc xử lý tình huống thực tế tương tự chưa?",
                        "placeholder": "Chọn mức độ kinh nghiệm thực hành của bạn...",
                        "question_type": "single_choice",
                        "type": "single_choice",
                        "options": [
                            "Chưa từng làm dự án, cần bài tập hướng dẫn từng bước",
                            "Đã làm bài tập nhỏ theo tutorial",
                            "Đã tự xây dự án hoàn chỉnh hoặc làm việc thực tế",
                            "Khác (mô tả kinh nghiệm thực hành của bạn)",
                        ],
                        "question_purpose": "Hiệu chỉnh độ khó của bài tập PRACTICE và tiêu chí đánh giá Prove Mode.",
                        "purpose": "Hiệu chỉnh độ khó của bài tập PRACTICE và tiêu chí đánh giá Prove Mode.",
                        "expected_answer_format": "Chọn 1 đáp án phù hợp nhất.",
                        "diagnostic_dimension": "PRACTICAL_EXPERIENCE",
                    },
                ]
                filtered = [
                    q for q in candidate_questions if q["diagnostic_dimension"] not in known_dims
                ]
                selected = (filtered if len(filtered) >= 3 else candidate_questions)[:5]
                if schema_name == "ClarificationFollowupLLMOutput":
                    selected = selected[:1]
                stub_payload["questions"] = [
                    {**q, "id": f"q{idx + 1}"} for idx, q in enumerate(selected)
                ]
                if schema_name != "ClarificationFollowupLLMOutput":
                    stub_payload["initial_assumptions"] = []
                    stub_payload["missing_dimensions"] = [
                        q["diagnostic_dimension"] for q in selected
                    ]
            else:
                stub_payload["questions"] = [
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
            ("score" in props and ("issues" in props or "advisory_warnings" in props))
            or "pedagogical_score" in props
            or "overall_status" in props
        ):
            judge_eval = _evaluate_pedagogical_quality_stub(effective_prompt)
            stub_payload.update(judge_eval)

        if "conceptual_understanding_score" in props:
            extracted_answers = re.findall(
                r'<learner_answer(?:\s+question_id="([^"]*)")?>(.*?)</learner_answer>',
                effective_prompt,
                flags=re.DOTALL | re.IGNORECASE,
            )
            non_trivial = [
                (qid or f"q{idx + 1}", ans.strip())
                for idx, (qid, ans) in enumerate(extracted_answers)
                if len(ans.strip()) >= 10
            ]
            if extracted_answers and len(non_trivial) == len(extracted_answers):
                stub_payload.update(
                    {
                        "conceptual_understanding_score": 34,
                        "example_grounding_score": 26,
                        "practical_application_score": 25,
                        "answer_evidence": [
                            {
                                "question_id": qid,
                                "evidence": "Câu trả lời thể hiện đúng bản chất và có dẫn chứng phù hợp.",
                                "is_addressed": True,
                            }
                            for qid, _ in non_trivial
                        ],
                        "corrective_action": None,
                    }
                )
            else:
                stub_payload.update(
                    {
                        "conceptual_understanding_score": 10,
                        "example_grounding_score": 8,
                        "practical_application_score": 7,
                        "answer_evidence": [
                            {
                                "question_id": (qid or f"q{idx + 1}"),
                                "evidence": "Câu trả lời quá ngắn hoặc thiếu giải thích bản chất và ví dụ.",
                                "is_addressed": False,
                            }
                            for idx, (qid, _ans) in enumerate(extracted_answers)
                        ]
                        or [
                            {
                                "question_id": "q1",
                                "evidence": "Chưa đủ nội dung để đánh giá hiểu bản chất.",
                                "is_addressed": False,
                            }
                        ],
                        "corrective_action": "Cần giải thích rõ nguyên lý, bổ sung ví dụ thực tế và cách vận dụng.",
                    }
                )
        elif "score" in props and "corrective_action" in props:
            stub_payload.update(
                {
                    "score": 85,
                    "status": "PASSED",
                    "corrective_action": None,
                }
            )

        if "strengths_feedback" in props and "bottlenecks_feedback" in props:
            stub_payload.update(
                {
                    "strengths_feedback": "Hoàn thành tốt các phiên học tập theo đúng dữ liệu thống kê tuần.",
                    "bottlenecks_feedback": "Cần duy trì nhịp độ ổn định và rà soát các khối học còn tồn đọng.",
                    "action_recommendations": "Ưu tiên thực hiện Prove Mode cho cột mốc trọng tâm tiếp theo.",
                }
            )

        validated_out = _normalize_schema_and_validate(stub_payload, response_schema)
        return LLMGenerationResult(
            payload=validated_out,
            prompt_tokens=128,
            output_tokens=256,
            thinking_tokens=0,
            model_id=self.last_model_used or self.model_used,
            raw_tool_results=tuple(tool_records),
        )

    async def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:
        _ = (system_prompt, user_prompt)
        chunks = [
            '{"stage": "analyzing_goal", "progress": 25}',
            '{"stage": "validating_dag_and_availability", "progress": 75}',
            '{"stage": "completed", "progress": 100}',
        ]
        for chunk in chunks:
            yield chunk
