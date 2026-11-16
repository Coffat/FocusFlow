"""Experiment 0.3: Schema enforcement across 5 cases x 3 modes x 10 runs = 150 sequential calls."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from common import (
    build_cobhub_client,
    build_genai_config,
    extract_response_telemetry,
    get_cobhub_config,
    get_prompt_template,
    parse_json_text,
    render_compact_schema_spec,
    sanitize_error_message,
    summarize_numeric,
    utc_timestamp,
    write_experiment_json,
)
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from src.evaluation.application.dtos.intelligence import ProveQuestionsLLMOutput
from src.evaluation.application.prompts import (
    PROVE_QUESTION_GENERATOR_PROMPT,
    build_prove_question_prompt,
)
from src.planning.application.dtos.planning_dtos import CriticQualityLLMOutput
from src.planning.application.services.roadmap_skills import COVERAGE_PREREQUISITE_CRITIC_PROMPT


class SimpleCheckSchema(BaseModel):
    ok: bool
    note: str = Field(..., min_length=1)


class SampleMilestoneItem(BaseModel):
    sequence_order: int = Field(ge=1)
    title: str
    description: str


class SampleRoadmapOutput(BaseModel):
    status: str
    summary: str
    milestones: list[SampleMilestoneItem] = Field(min_length=1)


MODES = (
    "mode1_response_json_schema_only",
    "mode2_system_compact_schema_only",
    "mode3_both_compact_and_response_schema",
)

RUNS_PER_CELL = 10


def _build_cases() -> list[dict[str, Any]]:
    critic_tpl = get_prompt_template(COVERAGE_PREREQUISITE_CRITIC_PROMPT.prompt_id)
    prove_tpl = get_prompt_template(PROVE_QUESTION_GENERATOR_PROMPT.prompt_id)

    critic_user_prompt = (
        "[INDEPENDENT_CRITIC:COVERAGE_PREREQUISITE_CRITIC]\n"
        "Stage=TASK_DECOMPOSITION\n"
        "Kiểm tra độ bao phủ, khoảng trống, trùng lặp và thứ tự tiên quyết.\n"
        "Không sửa payload và không dựa vào kết luận của critic khác; mọi issue phải nêu evidence/task_ref.\n"
        "learner_level: BEGINNER\n"
        "[CONTEXT]\nGoal: Học nền tảng Python & FastAPI trong 4 tuần\n"
        "[MILESTONES]\n"
        '[{"milestone_id": "m1", "sequence_order": 1, "title": "Python cơ bản", '
        '"learning_outcomes": ["Viết hàm và dùng dict/list"], "required_concepts": ["py-syntax-variables"]}]\n'
        "[PAYLOAD]\n"
        '{"tasks": ['
        '{"task_id": "T1", "milestone_id": "m1", "title": "Xây API FastAPI hoàn chỉnh", "task_type": "PROJECT", "estimated_minutes": 60, "covered_outcome_ids": ["M1-O1"], "concept_ids": ["py-syntax-variables"]}, '
        '{"task_id": "T2", "milestone_id": "m1", "title": "Học biến và hàm Python", "task_type": "THEORY", "estimated_minutes": 45, "covered_outcome_ids": ["M1-O1"], "concept_ids": ["py-syntax-variables"]}'
        '], "dependencies": [{"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": true}]}'
    )

    prove_user_prompt = build_prove_question_prompt(
        milestone_title="Chặng 1: Python cơ bản & kiểm soát luồng",
        description="Nắm vững biến, kiểu dữ liệu, vòng lặp, hàm và xử lý ngoại lệ.",
        learning_outcomes=[
            "Phân biệt list, tuple, dict, set và chọn cấu trúc phù hợp",
            "Viết hàm Python có type hint và xử lý ngoại lệ an toàn",
        ],
        completion_criteria="Giải thích được cơ chế tham chiếu đối tượng và viết được hàm xử lý dữ liệu không lỗi.",
        required_concepts=["py-syntax-variables", "py-control-flow-functions"],
        task_titles=[
            "Đọc lý thuyết biến và kiểu dữ liệu Python",
            "Thực hành viết hàm xử lý danh sách sinh viên",
        ],
    )

    return [
        {
            "case_id": "1_simple_schema",
            "schema_cls": SimpleCheckSchema,
            "system_prompt": "Bạn là trợ lý trả về JSON kiểm tra hệ thống.",
            "user_prompt": "Hãy trả về JSON xác nhận hệ thống sẵn sàng kèm ghi chú ngắn bằng tiếng Việt.",
            "use_tool": False,
        },
        {
            "case_id": "2_nested_sample_roadmap",
            "schema_cls": SampleRoadmapOutput,
            "system_prompt": "Bạn là chuyên gia lập lộ trình học tập.",
            "user_prompt": "Tạo 2 cột mốc học Python cơ bản cho người mới bắt đầu.",
            "use_tool": False,
        },
        {
            "case_id": "3_critic_quality_real",
            "schema_cls": CriticQualityLLMOutput,
            "system_prompt": critic_tpl.system_template,
            "user_prompt": critic_user_prompt,
            "use_tool": False,
        },
        {
            "case_id": "4_prove_questions_real",
            "schema_cls": ProveQuestionsLLMOutput,
            "system_prompt": prove_tpl.system_template,
            "user_prompt": prove_user_prompt,
            "use_tool": False,
        },
        {
            "case_id": "5_tool_to_json_two_turn",
            "schema_cls": SampleRoadmapOutput,
            "system_prompt": "Use the search_learning_concepts tool first, then return structured milestones.",
            "user_prompt": "Create 1 Python milestone using verified concepts from the tool.",
            "use_tool": True,
        },
    ]


def _compose_system_and_schema(
    base_system: str,
    schema_cls: type[BaseModel],
    mode: str,
) -> tuple[str, dict[str, Any] | None]:
    schema_dict = schema_cls.model_json_schema()
    if mode == "mode1_response_json_schema_only":
        return base_system, schema_dict
    compact_spec = render_compact_schema_spec(schema_cls)
    augmented = (
        f"{base_system}\n\n"
        "[OUTPUT_JSON_SCHEMA]: Chỉ trả về DUY NHẤT JSON khớp chính xác các trường, kiểu, enum và ràng buộc sau "
        "(không bỏ thiếu trường required):\n"
        f"{compact_spec}"
    )
    if mode == "mode2_system_compact_schema_only":
        return augmented, None
    return augmented, schema_dict


async def _run_single_call(
    client: Any,
    case: dict[str, Any],
    mode: str,
    model: str,
) -> dict[str, Any]:
    schema_cls: type[BaseModel] = case["schema_cls"]
    final_system, resp_schema = _compose_system_and_schema(
        case["system_prompt"], schema_cls, mode
    )
    t0 = time.perf_counter()
    p_tok = 0
    c_tok = 0
    t_tok = 0
    tot_tok = 0
    actual_model = model
    tool_called = False
    json_parsed = False
    pydantic_valid = False
    validation_errors: list[str] = []
    error_type: str | None = None
    error_message: str | None = None

    try:
        if not case["use_tool"]:
            cfg = build_genai_config(
                system_instruction=final_system,
                response_mime_type="application/json",
                response_json_schema=resp_schema,
                max_output_tokens=32768,
                thinking_level="LOW",
            )
            resp = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model,
                    contents=case["user_prompt"],
                    config=cfg,
                ),
                timeout=45.0,
            )
            tel = extract_response_telemetry(resp, model)
            p_tok = tel["prompt_tokens"]
            c_tok = tel["candidate_tokens"]
            t_tok = tel["thinking_tokens"]
            tot_tok = tel["total_tokens"]
            actual_model = tel["actual_model_id"]
        else:
            fn_decl = types.FunctionDeclaration(
                name="search_learning_concepts",
                description="Search verified learning concepts in the FocusFlow catalog.",
                parameters_json_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            )
            tool_cfg = build_genai_config(
                system_instruction=case["system_prompt"],
                tools=[types.Tool(function_declarations=[fn_decl])],
                thinking_level="LOW",
            )
            resp1 = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model,
                    contents=[case["user_prompt"]],
                    config=tool_cfg,
                ),
                timeout=30.0,
            )
            tel1 = extract_response_telemetry(resp1, model)
            p_tok += tel1["prompt_tokens"]
            c_tok += tel1["candidate_tokens"]
            t_tok += tel1["thinking_tokens"]
            tot_tok += tel1["total_tokens"]

            fn_calls = list(getattr(resp1, "function_calls", None) or [])
            cands = getattr(resp1, "candidates", None) or []
            model_content = getattr(cands[0], "content", None) if cands else None
            if not fn_calls and model_content is not None:
                for part in getattr(model_content, "parts", None) or []:
                    if getattr(part, "function_call", None) is not None:
                        fn_calls.append(part.function_call)

            contents_turn2: list[Any] = [case["user_prompt"]]
            if fn_calls:
                tool_called = True
                if model_content is not None:
                    contents_turn2.append(model_content)
                resp_parts: list[Any] = []
                for fc in fn_calls:
                    fc_name = str(getattr(fc, "name", "") or "search_learning_concepts")
                    fc_id = getattr(fc, "id", None)
                    tool_out = {
                        "concepts": [
                            {
                                "concept_id": "py-syntax-variables",
                                "title": "Python Syntax and Variables",
                            }
                        ]
                    }
                    part = types.Part.from_function_response(name=fc_name, response=tool_out)
                    if fc_id is not None and part.function_response is not None:
                        try:
                            part.function_response.id = str(fc_id)
                        except Exception:
                            pass
                    resp_parts.append(part)
                contents_turn2.append(types.Content(role="user", parts=resp_parts))
            else:
                contents_turn2.append(
                    "No tool call was made. Proceed directly to output valid JSON."
                )

            json_sys = (
                f"{final_system}\n\n"
                "[FINAL_OUTPUT_STAGE]: Không gọi thêm tool nào ở bước này. Chỉ xuất JSON hợp lệ."
            )
            json_cfg = build_genai_config(
                system_instruction=json_sys,
                response_mime_type="application/json",
                response_json_schema=resp_schema,
                max_output_tokens=32768,
                thinking_level="LOW",
            )
            resp = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model,
                    contents=contents_turn2,
                    config=json_cfg,
                ),
                timeout=45.0,
            )
            tel2 = extract_response_telemetry(resp, model)
            p_tok += tel2["prompt_tokens"]
            c_tok += tel2["candidate_tokens"]
            t_tok += tel2["thinking_tokens"]
            tot_tok += tel2["total_tokens"]
            actual_model = tel2["actual_model_id"]

        parsed = parse_json_text(getattr(resp, "text", None))
        json_parsed = True
        try:
            schema_cls.model_validate(parsed)
            pydantic_valid = True
        except ValidationError as ve:
            pydantic_valid = False
            error_type = "ValidationError"
            validation_errors = [
                f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}"
                for err in ve.errors()[:5]
            ]
            error_message = "; ".join(validation_errors)
    except Exception as exc:
        error_type = type(exc).__name__
        error_message = sanitize_error_message(exc)

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    return {
        "case_id": case["case_id"],
        "mode": mode,
        "actual_model_id": actual_model,
        "latency_ms": elapsed_ms,
        "prompt_tokens": p_tok,
        "candidate_tokens": c_tok,
        "thinking_tokens": t_tok,
        "total_tokens": tot_tok,
        "tool_called": tool_called if case["use_tool"] else None,
        "json_parsed": json_parsed,
        "pydantic_valid": pydantic_valid,
        "validation_errors": validation_errors,
        "error_type": error_type,
        "error_message": error_message,
    }


async def main() -> None:
    base_url, _ = get_cobhub_config()
    client = build_cobhub_client()
    model = "gemini-3.8-flash"
    cases = _build_cases()

    runs: list[dict[str, Any]] = []
    matrix_summary: dict[str, dict[str, Any]] = {}

    for case in cases:
        case_id = case["case_id"]
        matrix_summary[case_id] = {}
        for mode in MODES:
            cell_runs: list[dict[str, Any]] = []
            for idx in range(1, RUNS_PER_CELL + 1):
                rec = await _run_single_call(client, case, mode, model)
                rec["run_index"] = idx
                runs.append(rec)
                cell_runs.append(rec)
                print(
                    f"[0.3] case={case_id} mode={mode} run={idx:02d}/{RUNS_PER_CELL} "
                    f"json={rec['json_parsed']} valid={rec['pydantic_valid']} "
                    f"ms={rec['latency_ms']:.1f} err={rec['error_type']}",
                    flush=True,
                )
            valid_count = sum(1 for r in cell_runs if r["pydantic_valid"])
            json_count = sum(1 for r in cell_runs if r["json_parsed"])
            matrix_summary[case_id][mode] = {
                "total": len(cell_runs),
                "json_parsed_count": json_count,
                "pydantic_valid_count": valid_count,
                "pydantic_valid_rate": round(valid_count / len(cell_runs), 3),
                "latency_ms": summarize_numeric([r["latency_ms"] for r in cell_runs]),
                "prompt_tokens": summarize_numeric([float(r["prompt_tokens"]) for r in cell_runs]),
                "total_tokens": summarize_numeric([float(r["total_tokens"]) for r in cell_runs]),
                "sample_errors": [
                    r["error_message"] for r in cell_runs if r["error_message"]
                ][:3],
            }

    report = {
        "experiment": "0.3_schema_enforcement",
        "timestamp": utc_timestamp(),
        "base_url": base_url,
        "model": model,
        "runs_per_cell": RUNS_PER_CELL,
        "total_calls": len(runs),
        "matrix_summary": matrix_summary,
        "runs": runs,
    }
    out = write_experiment_json("exp_03_schema_enforcement.json", report)
    print(f"Saved: {out}")


if __name__ == "__main__":
    asyncio.run(main())
