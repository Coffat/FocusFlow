"""Experiment 0.9: Live Capability Probe (#8), Judge Calibration on 16 Bad Proposals & 54 Eval Runs (Mục A),
and Pure Quality A/B (-low vs -medium) for Milestone Planner + Task Decomposer across 5 Diverse Goals (Mục B).

Constraints:
- NEVER modifies production prompts (`roadmap_skills.py`, `prompts.py`, `prompts.lock`).
- NEVER reads/prints secrets, API keys, or PII.
- Executes all cobhub calls (`http://127.0.0.1:8045`) strictly sequentially.

Outputs:
- `/Users/vuthang/Documents/FocusFlow/docs/experiments/exp_09_judge_and_quality_ab.json`
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx

from common import (
    EXPERIMENTS_OUT_DIR,
    REPO_ROOT,
    build_cobhub_client,
    build_genai_config,
    extract_response_telemetry,
    get_cobhub_config,
    parse_json_text,
    percentile,
    sanitize_error_message,
    summarize_numeric,
    utc_timestamp,
    write_experiment_json,
)

from src.main import create_app, run_startup_ai_probe
from src.planning.application.dtos.planning_dtos import (
    MilestoneGenerationLLMOutput,
    TaskProposalLLMOutput,
)
from src.planning.application.services.knowledge_tool_dispatcher import (
    KnowledgeToolDispatcher,
    RoadmapPipelineStage,
)
from src.planning.application.services.roadmap_skills import (
    MILESTONE_PLANNER_SKILL,
    PEDAGOGICAL_JUDGE_SKILL,
    TASK_DECOMPOSER_SKILL,
    build_milestone_planner_prompt,
    build_planning_prompt_registry,
    build_task_decomposer_prompt,
)
from src.planning.application.services.validation_gate import (
    ProposalValidationGateOrchestrator,
    execute_tier3_pedagogical_judge,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    resolve_task_resources_from_tool_results,
)
from src.planning.domain.exceptions.planning_exceptions import ProposalValidationGateError
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
)
from src.planning.infrastructure.repositories.sqlalchemy_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)
from src.shared_kernel.application.harness.execution_manager import AIExecutionManager
from src.shared_kernel.application.harness.untrusted_context import (
    UntrustedBlockKind,
    format_untrusted_block,
    sanitize_untrusted_text,
)
from src.shared_kernel.application.llm_port import LLMGenerationResult
from src.shared_kernel.config import get_settings
from src.shared_kernel.domain.base import generate_uuid7
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import (
    LiteLLMAdapter,
    _GatewaySchemaProbeModel,
    clear_cobhub_capability_probe_cache,
)

OUTPUT_FILENAME = "exp_09_judge_and_quality_ab.json"
EVAL_RUN_FILES = (
    "group7_eval_run_1.json",
    "group7_eval_run_2.json",
    "group7_eval_run_3.json",
)


def _configure_env(base_url: str, api_key: str) -> None:
    os.environ["ENVIRONMENT"] = "development"
    os.environ["LLM_PROVIDER"] = "gemini"
    os.environ["LLM_BASE_URL"] = base_url
    if api_key and not os.environ.get("LLM_API_KEY"):
        os.environ["LLM_API_KEY"] = api_key
    os.environ["LLM_THINKING_CONTROL"] = "model_suffix"
    os.environ["LLM_MODEL"] = "gemini-3.8-flash-medium"
    os.environ["LLM_MODEL_LOW"] = "gemini-3.8-flash-low"
    os.environ["LLM_MODEL_MEDIUM"] = "gemini-3.8-flash-medium"
    os.environ["LLM_MODEL_HIGH"] = "gemini-3.8-flash-high"
    # Generous budgets for calibration & pure quality isolation (config validator: <= ai_hard_timeout_seconds)
    os.environ["AI_HARD_TIMEOUT_SECONDS"] = "260.0"
    os.environ["AI_SSE_PIPELINE_TIMEOUT_SECONDS"] = "250.0"
    os.environ["AI_MILESTONE_PLANNER_TIMEOUT_SECONDS"] = "120.0"
    os.environ["AI_TASK_DECOMPOSER_TIMEOUT_SECONDS"] = "120.0"
    os.environ["AI_TOOL_CALL_TIMEOUT_SECONDS"] = "45.0"
    os.environ["AI_QUALITY_CRITIC_TIMEOUT_SECONDS"] = "30.0"
    os.environ["AI_QUALITY_ARBITER_TIMEOUT_SECONDS"] = "30.0"
    os.environ["TIER3_JUDGE_TIMEOUT_SECONDS"] = "25.0"
    # Skip Dual Critics inside Step 2 so Step 2 isolates Decomposer + Tier 1/2 only
    os.environ["AI_MIN_CRITIC_REMAINING_SECONDS"] = "255.0"
    os.environ["AI_MIN_JUDGE_REMAINING_SECONDS"] = "3.0"
    os.environ["AI_MIN_RETRY_REMAINING_SECONDS"] = "12.0"
    get_settings.cache_clear()


class _TelemetryAdapter(LiteLLMAdapter):
    """Thin wrapper around LiteLLMAdapter to capture raw structured output, model_id, and wall latency."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[dict[str, Any]] = []

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | type[Any] | None = None,
        tools: list[Any] | None = None,
        tool_executor: Any = None,
        max_tool_calls: int = 2,
        thinking_level: str | None = None,
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> LLMGenerationResult:
        t0 = time.perf_counter()
        try:
            res = await super().generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
                tools=tools,
                tool_executor=tool_executor,
                max_tool_calls=max_tool_calls,
                thinking_level=thinking_level,
                timeout_seconds=timeout_seconds,
                tool_call_timeout_seconds=tool_call_timeout_seconds,
            )
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            self.calls.append(
                {
                    "ok": True,
                    "elapsed_ms": elapsed_ms,
                    "model_id": res.model_id,
                    "prompt_tokens": res.prompt_tokens,
                    "output_tokens": res.output_tokens,
                    "thinking_tokens": res.thinking_tokens,
                    "payload": res.payload,
                }
            )
            return res
        except BaseException as exc:
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            self.calls.append(
                {
                    "ok": False,
                    "elapsed_ms": elapsed_ms,
                    "error_type": type(exc).__name__,
                    "error_message": sanitize_error_message(exc),
                }
            )
            raise


# ---------------------------------------------------------------------------
# Part 1: Live Capability Probe (#8)
# ---------------------------------------------------------------------------
async def run_live_capability_probe(base_url: str) -> dict[str, Any]:
    print("\n=== [Part 1] Live Capability Probe (#8) ===", flush=True)
    clear_cobhub_capability_probe_cache()
    adapter = LiteLLMAdapter()
    probe_res = await adapter.probe_cobhub_capabilities(force=True)
    probe_dict = probe_res.to_dict()

    # Also capture schema_actual_model_id directly from Probe 1 (response_json_schema call)
    schema_actual_model_id: str | None = None
    schema_probe_error: str | None = None
    try:
        client = build_cobhub_client()
        probe1_cfg = build_genai_config(
            system_instruction="You are a minimal JSON health probe.",
            response_mime_type="application/json",
            response_json_schema=_GatewaySchemaProbeModel.model_json_schema(),
            max_output_tokens=128,
            thinking_level=None,
        )
        resp1 = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=probe_res.requested_low_model,
                contents="Return a valid JSON object.",
                config=probe1_cfg,
            ),
            timeout=10.0,
        )
        telemetry1 = extract_response_telemetry(resp1, probe_res.requested_low_model)
        schema_actual_model_id = telemetry1.get("actual_model_id")
    except Exception as exc:
        schema_probe_error = sanitize_error_message(exc)

    # Verify run_startup_ai_probe + GET /api/health?probe_ai=true
    startup_probe_dict: dict[str, Any] | None = None
    health_endpoint_result: dict[str, Any] = {}
    try:
        app = create_app()
        clear_cobhub_capability_probe_cache()
        startup_res = await run_startup_ai_probe(app)
        startup_probe_dict = startup_res.to_dict() if startup_res is not None else None
        clear_cobhub_capability_probe_cache()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as http_client:
            resp = await http_client.get("/api/health", params={"probe_ai": "true"})
            health_endpoint_result = {
                "status_code": resp.status_code,
                "body": resp.json(),
            }
    except Exception as exc:
        health_endpoint_result = {"error": sanitize_error_message(exc)}

    out = {
        "base_url": base_url,
        "schema_enforced_detected": probe_res.schema_enforced_detected,
        "schema_actual_model_id": schema_actual_model_id,
        "schema_probe_error": schema_probe_error,
        "low_model_requested": probe_res.requested_low_model,
        "low_actual_model_id": probe_res.actual_model_id,
        "low_model_thinking_tokens": probe_res.low_model_thinking_tokens,
        "low_thinking_is_low": probe_res.low_thinking_is_low,
        "warnings": list(probe_res.mismatches),
        "probe_result": probe_dict,
        "startup_ai_probe": startup_probe_dict,
        "health_probe_ai_true": health_endpoint_result,
    }
    print(
        f"[Probe #8] status={probe_dict['status']} schema_enforced={out['schema_enforced_detected']} "
        f"schema_model={schema_actual_model_id} low_req={out['low_model_requested']} "
        f"low_actual={out['low_actual_model_id']} low_think_tok={out['low_model_thinking_tokens']} "
        f"is_low={out['low_thinking_is_low']} warnings={out['warnings']}",
        flush=True,
    )
    return out


# ---------------------------------------------------------------------------
# Part 2A: 54-Run Baseline Eval Score Distribution
# ---------------------------------------------------------------------------
def analyze_54_eval_runs() -> dict[str, Any]:
    print("\n=== [Part 2A] 54-Run Eval Score Distribution ===", flush=True)
    all_scores: list[float] = []
    status_counts: Counter[str] = Counter()
    per_run_summaries: list[dict[str, Any]] = []

    for fname in EVAL_RUN_FILES:
        fpath = EXPERIMENTS_OUT_DIR / fname
        data = json.loads(fpath.read_text(encoding="utf-8"))
        outcomes = data.get("per_case_outcomes", [])
        run_scores = [
            float(o["pedagogical_score"])
            for o in outcomes
            if o.get("pedagogical_score") is not None
        ]
        run_statuses = Counter(str(o.get("judge_status") or "UNKNOWN") for o in outcomes)
        all_scores.extend(run_scores)
        status_counts.update(run_statuses)
        per_run_summaries.append(
            {
                "file": fname,
                "cases": len(outcomes),
                "min": min(run_scores) if run_scores else None,
                "median": percentile(run_scores, 50.0) if run_scores else None,
                "max": max(run_scores) if run_scores else None,
                "mean": round(statistics.mean(run_scores), 3) if run_scores else None,
                "statuses": dict(run_statuses),
            }
        )

    histogram = {
        str(int(k) if float(k).is_integer() else k): v
        for k, v in sorted(Counter(all_scores).items())
    }
    total = sum(status_counts.values())
    verdict_rates = {
        k: round(v / max(1, total), 4)
        for k, v in status_counts.items()
    }
    summary = {
        "total_runs": total,
        "scored_count": len(all_scores),
        "min": min(all_scores) if all_scores else None,
        "median": percentile(all_scores, 50.0) if all_scores else None,
        "p95": percentile(all_scores, 95.0) if all_scores else None,
        "max": max(all_scores) if all_scores else None,
        "mean": round(statistics.mean(all_scores), 3) if all_scores else None,
        "score_histogram": histogram,
        "verdict_counts": {
            "PASSED": status_counts.get("PASSED", 0),
            "NEEDS_REVIEW": status_counts.get("NEEDS_REVIEW", 0),
            "REVIEW_PENDING": status_counts.get("REVIEW_PENDING", 0),
            "SKIPPED": status_counts.get("SKIPPED", 0),
        },
        "verdict_rates": {
            "PASSED": verdict_rates.get("PASSED", 0.0),
            "NEEDS_REVIEW": verdict_rates.get("NEEDS_REVIEW", 0.0),
            "REVIEW_PENDING": verdict_rates.get("REVIEW_PENDING", 0.0),
            "SKIPPED": verdict_rates.get("SKIPPED", 0.0),
        },
        "per_run_file": per_run_summaries,
    }
    print(
        f"[54 Runs] n={total}, min={summary['min']}, median={summary['median']}, max={summary['max']}, "
        f"histogram={histogram}, verdicts={summary['verdict_counts']}",
        flush=True,
    )
    return summary


# ---------------------------------------------------------------------------
# Part 2B: 16 Intentional Bad Proposals for Judge Calibration
# ---------------------------------------------------------------------------
def _build_16_bad_proposals() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    # Group 1 (3 cases): outcome_coverage_gap
    cases.append(
        {
            "case_id": "BAD_01_COVERAGE_AUTH_HELLO_WORLD",
            "error_group": "outcome_coverage_gap",
            "error_description": "Milestone requires JWT auth, RBAC, and pytest integration tests; tasks only install pip packages and print Hello World.",
            "goal_title": "Xây dựng hệ thống xác thực FastAPI chuẩn production (JWT, RBAC, pytest)",
            "learner_level": "INTERMEDIATE",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: Xác thực JWT, Phân quyền RBAC & Kiểm thử tích hợp",
                    "learning_outcomes": [
                        "M1-O1: Triển khai đăng nhập, hash mật khẩu Argon2 và cấp phát JWT access/refresh token",
                        "M1-O2: Cài đặt phân quyền RBAC theo vai trò Admin/Learner bảo vệ endpoint",
                        "M1-O3: Viết bộ kiểm thử tích hợp pytest async bao phủ 401/403/200",
                    ],
                    "completion_criteria": "Hoàn thành hệ thống auth JWT + RBAC và vượt qua 100% pytest integration tests.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Cài đặt Python và FastAPI bằng pip",
                        "task_type": "THEORY",
                        "estimated_minutes": 45,
                        "learning_objective": "Chuẩn bị môi trường ảo venv và cài gói fastapi, uvicorn.",
                        "completion_criteria": "Chạy pip list thấy gói fastapi và uvicorn đã được cài.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Viết ứng dụng FastAPI Hello World đầu tiên",
                        "task_type": "PRACTICE",
                        "estimated_minutes": 45,
                        "learning_objective": "Tạo endpoint GET / trả về JSON hello world.",
                        "completion_criteria": "Mở localhost:8000/ thấy dòng chữ {\"message\": \"Hello World\"}.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": ["T1"],
                    },
                ],
                "dependencies": [{"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True}],
            },
        }
    )

    cases.append(
        {
            "case_id": "BAD_02_COVERAGE_SQL_MIGRATION_MISSING",
            "error_group": "outcome_coverage_gap",
            "error_description": "Milestone requires PostgreSQL indexing, deadlock prevention, and zero-downtime Alembic migrations; tasks only install Postgres and create 1 trivial table.",
            "goal_title": "Thành thạo PostgreSQL Indexing, Transaction & Alembic Migration",
            "learner_level": "INTERMEDIATE",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: PostgreSQL Indexing, MVCC Deadlock & Alembic Expand-Contract",
                    "learning_outcomes": [
                        "M1-O1: Thiết kế B-Tree, GIN index và tối ưu truy vấn qua EXPLAIN ANALYZE",
                        "M1-O2: Xử lý Transaction Isolation và phòng tránh deadlock khi ghi đồng thời",
                        "M1-O3: Viết Alembic migration theo mẫu Expand-Contract không downtime",
                    ],
                    "completion_criteria": "Giảm thời gian truy vấn < 10ms, xử lý deadlock an toàn và chạy migration upgrade/downgrade sạch.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Cài đặt PostgreSQL trên máy cá nhân và mở psql",
                        "task_type": "THEORY",
                        "estimated_minutes": 45,
                        "learning_objective": "Cài xong dịch vụ PostgreSQL local và kết nối bằng CLI.",
                        "completion_criteria": "Chạy SELECT version() thành công trong psql.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Tạo bảng notes đơn giản và chèn 2 dòng dữ liệu mẫu",
                        "task_type": "PRACTICE",
                        "estimated_minutes": 45,
                        "learning_objective": "Thực hành lệnh CREATE TABLE và INSERT cơ bản.",
                        "completion_criteria": "Chạy SELECT * FROM notes hiển thị 2 dòng dữ liệu.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": ["T1"],
                    },
                ],
                "dependencies": [{"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True}],
            },
        }
    )

    cases.append(
        {
            "case_id": "BAD_03_COVERAGE_ANGULAR_TESTING_GAP",
            "error_group": "outcome_coverage_gap",
            "error_description": "Milestone requires Angular Signals, Reactive Forms validation, Vitest unit tests, and Playwright E2E; tasks only scaffold Angular CLI and render static HTML.",
            "goal_title": "Phát triển ứng dụng Angular Signals, Reactive Forms & Kiểm thử E2E",
            "learner_level": "INTERMEDIATE",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: Angular Signals, Reactive Form Validators & Vitest/Playwright",
                    "learning_outcomes": [
                        "M1-O1: Quản lý state với signal(), computed() và effect() không dùng NgRx",
                        "M1-O2: Xây dựng Reactive Form có async custom validator và thông báo lỗi ARIA",
                        "M1-O3: Viết bộ unit test Vitest và E2E test Playwright cho luồng đăng ký",
                    ],
                    "completion_criteria": "Ứng dụng form chạy hoàn chỉnh, đạt >= 90% coverage trên Vitest và pass E2E Playwright.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Cài đặt Node.js và khởi tạo dự án bằng Angular CLI",
                        "task_type": "THEORY",
                        "estimated_minutes": 40,
                        "learning_objective": "Tạo thư mục dự án Angular mới với lệnh ng new.",
                        "completion_criteria": "Chạy ng serve hiển thị trang chào mừng mặc định của Angular.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Sửa tiêu đề HTML tĩnh trong app.component.html",
                        "task_type": "PRACTICE",
                        "estimated_minutes": 40,
                        "learning_objective": "Đổi thẻ h1 thành tên ứng dụng.",
                        "completion_criteria": "Trình duyệt hiển thị dòng tiêu đề tĩnh mới.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": ["T1"],
                    },
                ],
                "dependencies": [{"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True}],
            },
        }
    )

    # Group 2 (3 cases): dependency_cycle_or_inverted_order
    cases.append(
        {
            "case_id": "BAD_04_INVERTED_DEPLOY_BEFORE_BASICS",
            "error_group": "dependency_cycle_or_inverted_order",
            "error_description": "T1 (PROJECT: Deploy microservices to production Kubernetes) is prerequisite BEFORE T2 (PRACTICE CRUD) and T3 (THEORY Python/HTTP basics).",
            "goal_title": "Docker & FastAPI Backend cho người mới bắt đầu",
            "learner_level": "BEGINNER",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: Nền tảng HTTP, FastAPI CRUD & Triển khai Docker",
                    "learning_outcomes": [
                        "M1-O1: Hiểu giao thức HTTP và viết API FastAPI cơ bản",
                        "M1-O2: Đóng gói và triển khai dịch vụ với Docker",
                    ],
                    "completion_criteria": "API FastAPI chạy ổn định trong container Docker.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Triển khai hệ thống microservices lên Kubernetes production với Helm & TLS",
                        "task_type": "PROJECT",
                        "estimated_minutes": 90,
                        "learning_objective": "Vận hành cụm K8s production với autoscaling và TLS ingress.",
                        "completion_criteria": "Hệ thống microservices chạy trên Kubernetes cluster có HTTPS.",
                        "covered_outcome_ids": ["M1-O2"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Thực hành viết endpoint FastAPI CRUD đầu tiên",
                        "task_type": "PRACTICE",
                        "estimated_minutes": 60,
                        "learning_objective": "Viết 4 route GET/POST/PUT/DELETE cơ bản.",
                        "completion_criteria": "Test các endpoint trên Swagger UI trả về 200 OK.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": ["T1"],
                    },
                    {
                        "task_id": "T3",
                        "milestone_id": "m1",
                        "title": "Học lý thuyết biến Python và khái niệm HTTP Request/Response cơ bản",
                        "task_type": "THEORY",
                        "estimated_minutes": 45,
                        "learning_objective": "Hiểu method GET/POST và cú pháp hàm Python.",
                        "completion_criteria": "Hoàn thành bài trắc nghiệm 10 câu về HTTP status codes.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": ["T2"],
                    },
                ],
                "dependencies": [
                    {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
                    {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
                ],
            },
        }
    )

    cases.append(
        {
            "case_id": "BAD_05_EXPLICIT_CYCLE_DAG",
            "error_group": "dependency_cycle_or_inverted_order",
            "error_description": "Explicit circular dependency cycle T1 -> T2 -> T3 -> T1 in dependencies and depends_on_task_ids.",
            "goal_title": "Cấu trúc dữ liệu & Giải thuật Đồ thị",
            "learner_level": "INTERMEDIATE",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: Duyệt đồ thị BFS/DFS, Dijkstra & Topological Sort",
                    "learning_outcomes": [
                        "M1-O1: Cài đặt BFS/DFS và tìm đường đi ngắn nhất Dijkstra",
                        "M1-O2: Phát hiện chu trình và sắp xếp topo bằng thuật toán Kahn",
                    ],
                    "completion_criteria": "Giải thành công 6 bài tập đồ thị với độ phức tạp tối ưu.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Lý thuyết biểu diễn đồ thị & BFS/DFS",
                        "task_type": "THEORY",
                        "estimated_minutes": 60,
                        "learning_objective": "Nắm vững danh sách kề và duyệt theo chiều rộng/sâu.",
                        "completion_criteria": "Cài đặt BFS và DFS vượt qua 5 test case mẫu.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": ["T3"],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Thực hành thuật toán Dijkstra bằng Min-Heap",
                        "task_type": "PRACTICE",
                        "estimated_minutes": 75,
                        "learning_objective": "Tìm đường đi ngắn nhất trên đồ thị có trọng số dương.",
                        "completion_criteria": "Pass 3 bài Dijkstra trên đồ thị 10^5 đỉnh trong < 1s.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": ["T1"],
                    },
                    {
                        "task_id": "T3",
                        "milestone_id": "m1",
                        "title": "Dự án mini: Bộ kiểm tra DAG & Topological Sort",
                        "task_type": "PROJECT",
                        "estimated_minutes": 90,
                        "learning_objective": "Phát hiện chu trình và sắp xếp thứ tự phụ thuộc.",
                        "completion_criteria": "Viết unit test chứng minh phát hiện được chu trình trong đồ thị.",
                        "covered_outcome_ids": ["M1-O2"],
                        "depends_on_task_ids": ["T2"],
                    },
                ],
                "dependencies": [
                    {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
                    {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
                    {"predecessor_id": "T3", "successor_id": "T1", "is_mandatory": True},
                ],
            },
        }
    )

    cases.append(
        {
            "case_id": "BAD_06_FORWARD_DEP_AND_REVERSE_FLOW",
            "error_group": "dependency_cycle_or_inverted_order",
            "error_description": "T2 depends on T3 which stands after it, mutual cycle T2 <-> T3, and PROJECT T1 stands before THEORY T3.",
            "goal_title": "Xây dựng ứng dụng Todo với React & TypeScript",
            "learner_level": "BEGINNER",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: JSX, TypeScript Props & Ứng dụng Todo",
                    "learning_outcomes": [
                        "M1-O1: Tạo component React với TypeScript interface props và state",
                        "M1-O2: Xây dựng ứng dụng Todo có thêm/sửa/xóa và lưu localStorage",
                    ],
                    "completion_criteria": "Hoàn thành ứng dụng Todo không lỗi TypeScript.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Dự án hoàn chỉnh: Triển khai ứng dụng Todo tích hợp localStorage & CI",
                        "task_type": "PROJECT",
                        "estimated_minutes": 90,
                        "learning_objective": "Đóng gói và triển khai ứng dụng Todo hoàn chỉnh.",
                        "completion_criteria": "Ứng dụng Todo chạy trên production URL.",
                        "covered_outcome_ids": ["M1-O2"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Ôn tập kiến thức JSX và state nâng cao",
                        "task_type": "REVIEW",
                        "estimated_minutes": 45,
                        "learning_objective": "Củng cố vòng đời render và state trong React.",
                        "completion_criteria": "Hoàn thành 5 câu hỏi ôn tập JSX và state.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": ["T1", "T3"],
                    },
                    {
                        "task_id": "T3",
                        "milestone_id": "m1",
                        "title": "Học cú pháp JSX và định nghĩa Props cơ bản",
                        "task_type": "THEORY",
                        "estimated_minutes": 60,
                        "learning_objective": "Hiểu cách truyền dữ liệu giữa các component.",
                        "completion_criteria": "Viết được 2 component Button và Card nhận props có kiểu rõ ràng.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": ["T2"],
                    },
                ],
                "dependencies": [
                    {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
                    {"predecessor_id": "T3", "successor_id": "T2", "is_mandatory": True},
                    {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
                ],
            },
        }
    )

    # Group 3 (3 cases): duration_exceeds_120m (150, 180, 240)
    cases.append(
        {
            "case_id": "BAD_07_DURATION_150M",
            "error_group": "duration_exceeds_120m",
            "error_description": "Task T2 has estimated_minutes=150 (exceeds SRS 30..120m cognitive bound).",
            "goal_title": "Lập trình bất đồng bộ Python AsyncIO",
            "learner_level": "INTERMEDIATE",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: Coroutines, asyncio.gather & Web Crawler bất đồng bộ",
                    "learning_outcomes": [
                        "M1-O1: Sử dụng async/await và asyncio.gather an toàn với Semaphore",
                        "M1-O2: Xử lý timeout và cancellation cho tác vụ I/O",
                    ],
                    "completion_criteria": "Crawler bất đồng bộ thu thập 50 trang với rate limit ổn định.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Lý thuyết Event Loop, Coroutine và Task trong asyncio",
                        "task_type": "THEORY",
                        "estimated_minutes": 60,
                        "learning_objective": "Hiểu cơ chế lập lịch hợp tác và không chặn event loop.",
                        "completion_criteria": "Giải thích được sự khác biệt giữa asyncio.gather và TaskGroup.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Thực hành viết Async Web Crawler đầy đủ Semaphore, retry và benchmark trong một phiên dài",
                        "task_type": "PRACTICE",
                        "estimated_minutes": 150,
                        "learning_objective": "Xây dựng crawler bất đồng bộ có giới hạn đồng thời và timeout.",
                        "completion_criteria": "Crawler chạy xong 50 URL mẫu với benchmark tốc độ và unit test pass.",
                        "covered_outcome_ids": ["M1-O1", "M1-O2"],
                        "depends_on_task_ids": ["T1"],
                    },
                    {
                        "task_id": "T3",
                        "milestone_id": "m1",
                        "title": "Ôn tập xử lý CancelledError và timeout",
                        "task_type": "REVIEW",
                        "estimated_minutes": 45,
                        "learning_objective": "Kiểm soát dọn dẹp tài nguyên khi coroutine bị hủy.",
                        "completion_criteria": "Pass 3 test case mô phỏng timeout bằng asyncio.wait_for.",
                        "covered_outcome_ids": ["M1-O2"],
                        "depends_on_task_ids": ["T2"],
                    },
                ],
                "dependencies": [
                    {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
                    {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
                ],
            },
        }
    )

    cases.append(
        {
            "case_id": "BAD_08_DURATION_180M",
            "error_group": "duration_exceeds_120m",
            "error_description": "Task T2 has estimated_minutes=180 (3-hour monolithic session violating SRS 30..120m).",
            "goal_title": "Thiết kế Cơ sở dữ liệu Quan hệ & SQL",
            "learner_level": "BEGINNER",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: Chuẩn hóa 3NF & Truy vấn SQL JOIN",
                    "learning_outcomes": [
                        "M1-O1: Chuẩn hóa lược đồ bảng đạt chuẩn 3NF",
                        "M1-O2: Viết thành thạo INNER/LEFT JOIN và GROUP BY",
                    ],
                    "completion_criteria": "Thiết kế CSDL quản lý thư viện đạt 3NF và pass 10 truy vấn báo cáo.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Lý thuyết khóa chính, khóa ngoại và chuẩn 1NF-3NF",
                        "task_type": "THEORY",
                        "estimated_minutes": 45,
                        "learning_objective": "Nhận diện dư thừa dữ liệu và phụ thuộc bắc cầu.",
                        "completion_criteria": "Tách đúng 1 bảng chưa chuẩn hóa thành 3 bảng đạt 3NF.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Thực hành chuẩn hóa toàn bộ schema và viết 20 câu JOIN phức tạp liên tục 3 tiếng",
                        "task_type": "PRACTICE",
                        "estimated_minutes": 180,
                        "learning_objective": "Thành thạo thiết kế bảng và truy vấn đa bảng.",
                        "completion_criteria": "Hoàn thành và kiểm tra kết quả 20 câu SQL trên PostgreSQL.",
                        "covered_outcome_ids": ["M1-O1", "M1-O2"],
                        "depends_on_task_ids": ["T1"],
                    },
                    {
                        "task_id": "T3",
                        "milestone_id": "m1",
                        "title": "Dự án mini: Lược đồ quản lý mượn trả sách thư viện",
                        "task_type": "PROJECT",
                        "estimated_minutes": 90,
                        "learning_objective": "Áp dụng 3NF và JOIN vào bài toán thực tế.",
                        "completion_criteria": "Chạy file schema.sql và 5 truy vấn thống kê không lỗi.",
                        "covered_outcome_ids": ["M1-O1", "M1-O2"],
                        "depends_on_task_ids": ["T2"],
                    },
                ],
                "dependencies": [
                    {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
                    {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
                ],
            },
        }
    )

    cases.append(
        {
            "case_id": "BAD_09_DURATION_240M",
            "error_group": "duration_exceeds_120m",
            "error_description": "Task T2 has estimated_minutes=240 (4-hour monolithic session violating SRS 30..120m).",
            "goal_title": "Kubernetes & Monitoring Stack chuyên sâu",
            "learner_level": "ADVANCED",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: Quan sát hệ thống với Prometheus & Grafana trên K8s",
                    "learning_outcomes": [
                        "M1-O1: Cấu hình ServiceMonitor và thu thập metrics RED/USE",
                        "M1-O2: Thiết lập cảnh báo SLO burn-rate với Alertmanager",
                    ],
                    "completion_criteria": "Dashboard Grafana và rule cảnh báo burn-rate hoạt động trên cụm K8s.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Lý thuyết kiến trúc Prometheus Operator và SLO burn-rate",
                        "task_type": "THEORY",
                        "estimated_minutes": 60,
                        "learning_objective": "Hiểu cơ chế scrape CRD ServiceMonitor và multi-window alert.",
                        "completion_criteria": "Viết đúng công thức PromQL tính error budget burn rate.",
                        "covered_outcome_ids": ["M1-O1", "M1-O2"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Dự án triển khai trọn bộ Kubernetes, Prometheus, Grafana, Loki và Alertmanager trong 4 giờ liền",
                        "task_type": "PROJECT",
                        "estimated_minutes": 240,
                        "learning_objective": "Dựng toàn bộ stack observability từ đầu tới cuối không chia nhỏ.",
                        "completion_criteria": "Toàn bộ pod monitoring Running và kích hoạt test alert thành công.",
                        "covered_outcome_ids": ["M1-O1", "M1-O2"],
                        "depends_on_task_ids": ["T1"],
                    },
                    {
                        "task_id": "T3",
                        "milestone_id": "m1",
                        "title": "Ôn tập tinh chỉnh cardinality và retention",
                        "task_type": "REVIEW",
                        "estimated_minutes": 45,
                        "learning_objective": "Giảm chi phí RAM cho TSDB Prometheus.",
                        "completion_criteria": "Xác định và loại bỏ được ít nhất 2 label gây high-cardinality.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": ["T2"],
                    },
                ],
                "dependencies": [
                    {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
                    {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
                ],
            },
        }
    )

    # Group 4 (3 cases): unmeasurable_criteria
    cases.append(
        {
            "case_id": "BAD_10_VAGUE_UNDERSTAND_CONCEPT",
            "error_group": "unmeasurable_criteria",
            "error_description": "Completion criteria and learning objectives are vague and non-verifiable ('hiểu khái niệm', 'nắm vững tổng quan', 'đọc thêm cho biết').",
            "goal_title": "Học lập trình hướng đối tượng (OOP) trong Python",
            "learner_level": "BEGINNER",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: Class, Đóng gói & Kế thừa trong Python",
                    "learning_outcomes": [
                        "M1-O1: Định nghĩa class với __init__, phương thức và thuộc tính đóng gói",
                        "M1-O2: Áp dụng kế thừa và đa hình giải bài toán quản lý nhân sự",
                    ],
                    "completion_criteria": "Hoàn thành bài tập OOP quản lý nhân sự vượt qua unit test.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Tìm hiểu class và object trong Python",
                        "task_type": "THEORY",
                        "estimated_minutes": 45,
                        "learning_objective": "Biết sơ qua về OOP.",
                        "completion_criteria": "Hiểu khái niệm.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Xem về kế thừa và đa hình",
                        "task_type": "THEORY",
                        "estimated_minutes": 60,
                        "learning_objective": "Làm quen với kế thừa.",
                        "completion_criteria": "Nắm vững tổng quan.",
                        "covered_outcome_ids": ["M1-O2"],
                        "depends_on_task_ids": ["T1"],
                    },
                    {
                        "task_id": "T3",
                        "milestone_id": "m1",
                        "title": "Đọc thêm tài liệu về thiết kế hướng đối tượng",
                        "task_type": "REVIEW",
                        "estimated_minutes": 45,
                        "learning_objective": "Mở rộng kiến thức.",
                        "completion_criteria": "Đọc thêm cho biết.",
                        "covered_outcome_ids": ["M1-O1", "M1-O2"],
                        "depends_on_task_ids": ["T2"],
                    },
                ],
                "dependencies": [
                    {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
                    {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
                ],
            },
        }
    )

    cases.append(
        {
            "case_id": "BAD_11_VAGUE_NO_DELIVERABLE",
            "error_group": "unmeasurable_criteria",
            "error_description": "Tasks have no concrete deliverables/tests; criteria say 'cảm thấy tự tin', 'đọc xong tài liệu', 'hiểu sơ bộ cách hoạt động'.",
            "goal_title": "System Design Caching & Message Queue",
            "learner_level": "INTERMEDIATE",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: Redis Caching Patterns & Kafka/RabbitMQ",
                    "learning_outcomes": [
                        "M1-O1: So sánh và cài đặt Cache-Aside vs Write-Through",
                        "M1-O2: Thiết kế luồng xử lý bất đồng bộ với Dead-Letter Queue",
                    ],
                    "completion_criteria": "Có sơ đồ kiến trúc và benchmark thử nghiệm cache hit ratio + DLQ retry.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Nghiên cứu về bộ nhớ đệm Redis",
                        "task_type": "THEORY",
                        "estimated_minutes": 60,
                        "learning_objective": "Tìm hiểu các mẫu caching phổ biến.",
                        "completion_criteria": "Hiểu sơ bộ cách hoạt động.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Tìm hiểu hàng đợi thông điệp và DLQ",
                        "task_type": "THEORY",
                        "estimated_minutes": 60,
                        "learning_objective": "Biết vai trò của message queue.",
                        "completion_criteria": "Đọc xong tài liệu tham khảo.",
                        "covered_outcome_ids": ["M1-O2"],
                        "depends_on_task_ids": ["T1"],
                    },
                    {
                        "task_id": "T3",
                        "milestone_id": "m1",
                        "title": "Tự suy ngẫm về khả năng mở rộng hệ thống",
                        "task_type": "REVIEW",
                        "estimated_minutes": 45,
                        "learning_objective": "Củng cố tư duy kiến trúc.",
                        "completion_criteria": "Cảm thấy tự tin về lý thuyết.",
                        "covered_outcome_ids": ["M1-O1", "M1-O2"],
                        "depends_on_task_ids": ["T2"],
                    },
                ],
                "dependencies": [
                    {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
                    {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
                ],
            },
        }
    )

    cases.append(
        {
            "case_id": "BAD_12_VAGUE_READ_ONLY",
            "error_group": "unmeasurable_criteria",
            "error_description": "Passive read-only tasks with non-measurable criteria ('đọc hết bài mẫu cho biết', 'nắm được tinh thần chung', 'xem qua vài từ vựng').",
            "goal_title": "Luyện thi IELTS Academic Writing Task 2",
            "learner_level": "INTERMEDIATE",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: Cấu trúc bài luận Opinion & Coherence/Cohesion",
                    "learning_outcomes": [
                        "M1-O1: Lập dàn ý 4 đoạn theo tiêu chí Task Response band 7.0",
                        "M1-O2: Viết hoàn chỉnh bài luận 250+ từ trong 40 phút và tự chấm",
                    ],
                    "completion_criteria": "Viết và tự chấm ít nhất 2 bài luận Task 2 >= 250 từ đúng thời gian.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Làm quen với dạng đề Opinion",
                        "task_type": "THEORY",
                        "estimated_minutes": 45,
                        "learning_objective": "Biết cách người ta viết mở bài và thân bài.",
                        "completion_criteria": "Nắm được tinh thần chung của IELTS Writing.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Xem bộ sưu tập các bài văn mẫu điểm cao",
                        "task_type": "THEORY",
                        "estimated_minutes": 60,
                        "learning_objective": "Tham khảo cách dùng câu của giám khảo.",
                        "completion_criteria": "Đọc hết bài mẫu cho biết.",
                        "covered_outcome_ids": ["M1-O1", "M1-O2"],
                        "depends_on_task_ids": ["T1"],
                    },
                    {
                        "task_id": "T3",
                        "milestone_id": "m1",
                        "title": "Lướt danh sách từ vựng học thuật",
                        "task_type": "REVIEW",
                        "estimated_minutes": 30,
                        "learning_objective": "Nhớ mặt chữ một số từ hay.",
                        "completion_criteria": "Xem qua vài từ vựng.",
                        "covered_outcome_ids": ["M1-O2"],
                        "depends_on_task_ids": ["T2"],
                    },
                ],
                "dependencies": [
                    {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
                    {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
                ],
            },
        }
    )

    # Group 5 (4 cases): off_domain_or_level_mismatch
    cases.append(
        {
            "case_id": "BAD_13_DOMAIN_PHO_COOKING",
            "error_group": "off_domain_or_level_mismatch",
            "error_description": "Goal is 'Backend FastAPI & PostgreSQL', but all tasks teach cooking Vietnamese Pho soup.",
            "goal_title": "Backend FastAPI & PostgreSQL",
            "learner_level": "BEGINNER",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: Xây dựng REST API với FastAPI & PostgreSQL",
                    "learning_outcomes": [
                        "M1-O1: Tạo REST API CRUD bằng FastAPI và Pydantic v2",
                        "M1-O2: Lưu trữ và truy vấn dữ liệu trên PostgreSQL với SQLAlchemy 2.0",
                    ],
                    "completion_criteria": "API FastAPI kết nối PostgreSQL chạy đầy đủ CRUD với pytest.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Lý thuyết chọn xương ống bò và gia vị nấu nước dùng Phở Hà Nội",
                        "task_type": "THEORY",
                        "estimated_minutes": 45,
                        "learning_objective": "Phân biệt hoa hồi, thảo quả, quế chi và cách chần xương sạch mùi.",
                        "completion_criteria": "Liệt kê đủ 7 loại gia vị và tỷ lệ xương/nước chuẩn.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Thực hành nướng hành gừng, rang thảo mộc và ninh nồi nước dùng trong 6 tiếng",
                        "task_type": "PRACTICE",
                        "estimated_minutes": 90,
                        "learning_objective": "Nấu được nước dùng trong, ngọt thanh và dậy mùi thơm.",
                        "completion_criteria": "Nước dùng trong suốt, nêm nếm cân bằng mặn ngọt.",
                        "covered_outcome_ids": ["M1-O2"],
                        "depends_on_task_ids": ["T1"],
                    },
                    {
                        "task_id": "T3",
                        "milestone_id": "m1",
                        "title": "Dự án hoàn thiện: Trần bánh phở, thái thịt bò tái chín và trình bày tô phở",
                        "task_type": "PROJECT",
                        "estimated_minutes": 60,
                        "learning_objective": "Hoàn thành 2 tô phở bò đạt chuẩn vị truyền thống.",
                        "completion_criteria": "Phục vụ 2 tô phở nóng hổi với bánh phở mềm dai không nát.",
                        "covered_outcome_ids": ["M1-O1", "M1-O2"],
                        "depends_on_task_ids": ["T2"],
                    },
                ],
                "dependencies": [
                    {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
                    {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
                ],
            },
        }
    )

    cases.append(
        {
            "case_id": "BAD_14_DOMAIN_CANVA_POSTER",
            "error_group": "off_domain_or_level_mismatch",
            "error_description": "Goal is 'Backend FastAPI & PostgreSQL', but tasks teach designing marketing posters in Canva.",
            "goal_title": "Backend FastAPI & PostgreSQL",
            "learner_level": "INTERMEDIATE",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: Thiết kế Schema SQL & Bảo mật API FastAPI",
                    "learning_outcomes": [
                        "M1-O1: Thiết kế mô hình dữ liệu PostgreSQL chuẩn 3NF",
                        "M1-O2: Triển khai FastAPI Dependency Injection và xác thực JWT",
                    ],
                    "completion_criteria": "Hệ thống API bảo mật chạy ổn định với dữ liệu lưu trên PostgreSQL.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Lý thuyết bánh xe màu sắc pastel và cặp font chữ cho poster quảng cáo",
                        "task_type": "THEORY",
                        "estimated_minutes": 45,
                        "learning_objective": "Chọn bảng màu hài hòa và font sans-serif hiện đại trên Canva.",
                        "completion_criteria": "Tạo được moodboard gồm 3 bảng màu và 2 cặp font.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Thực hành thiết kế poster khuyến mãi trà sữa kích thước Instagram trên Canva",
                        "task_type": "PRACTICE",
                        "estimated_minutes": 60,
                        "learning_objective": "Sắp xếp bố cục 1/3, chèn sticker và hiệu ứng đổ bóng chữ.",
                        "completion_criteria": "Hoàn thành 1 mẫu poster 1080x1350px đúng nhận diện thương hiệu.",
                        "covered_outcome_ids": ["M1-O2"],
                        "depends_on_task_ids": ["T1"],
                    },
                    {
                        "task_id": "T3",
                        "milestone_id": "m1",
                        "title": "Dự án xuất bản bộ 3 banner quảng cáo Facebook bằng Canva Pro",
                        "task_type": "PROJECT",
                        "estimated_minutes": 60,
                        "learning_objective": "Xuất file PNG độ phân giải cao và resize đa kênh.",
                        "completion_criteria": "Xuất thành công 3 file PNG đạt độ nét 300 DPI.",
                        "covered_outcome_ids": ["M1-O1", "M1-O2"],
                        "depends_on_task_ids": ["T2"],
                    },
                ],
                "dependencies": [
                    {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
                    {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
                ],
            },
        }
    )

    cases.append(
        {
            "case_id": "BAD_15_LEVEL_BEGINNER_TO_ADVANCED_KERNEL",
            "error_group": "off_domain_or_level_mismatch",
            "error_description": "Learner is BEGINNER wanting basic Python variables/loops, but tasks jump straight into Linux eBPF kernel, Raft consensus, and CUDA C++.",
            "goal_title": "Python cơ bản từ con số 0 cho người mới bắt đầu",
            "learner_level": "BEGINNER",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: Biến, vòng lặp và hàm cơ bản trong Python",
                    "learning_outcomes": [
                        "M1-O1: Sử dụng biến, kiểu dữ liệu số/chuỗi và rẽ nhánh if/else",
                        "M1-O2: Viết vòng lặp for/while và hàm Python đơn giản",
                    ],
                    "completion_criteria": "Viết được chương trình tính điểm trung bình và bảng cửu chương bằng Python.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Lý thuyết viết eBPF XDP packet filter bằng C gắn trực tiếp vào Linux kernel",
                        "task_type": "THEORY",
                        "estimated_minutes": 90,
                        "learning_objective": "Nắm vững verifier của Linux kernel, ring buffer và XDP_DROP.",
                        "completion_criteria": "Biên dịch thành công bytecode eBPF với clang và attach lên NIC.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Thực hành triển khai thuật toán đồng thuận Raft multi-node chịu lỗi Byzantine bằng Rust",
                        "task_type": "PRACTICE",
                        "estimated_minutes": 90,
                        "learning_objective": "Xử lý leader election, log compaction và Jepsen partition tests.",
                        "completion_criteria": "Cụm 5 node vượt qua kiểm thử chia cắt mạng không mất log.",
                        "covered_outcome_ids": ["M1-O2"],
                        "depends_on_task_ids": ["T1"],
                    },
                    {
                        "task_id": "T3",
                        "milestone_id": "m1",
                        "title": "Dự án viết CUDA C++ kernel tối ưu shared-memory matrix multiplication trên GPU",
                        "task_type": "PROJECT",
                        "estimated_minutes": 120,
                        "learning_objective": "Loại bỏ bank conflict và đạt >= 80% peak FLOPS của GPU.",
                        "completion_criteria": "Benchmark đạt tốc độ trong phạm vi 15% so với cuBLAS.",
                        "covered_outcome_ids": ["M1-O1", "M1-O2"],
                        "depends_on_task_ids": ["T2"],
                    },
                ],
                "dependencies": [
                    {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
                    {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
                ],
            },
        }
    )

    cases.append(
        {
            "case_id": "BAD_16_MIXED_GOALS_DRIFT",
            "error_group": "off_domain_or_level_mismatch",
            "error_description": "Goal is 'Financial Data Analysis with Python Pandas', but tasks mix French pronunciation, woodworking varnish, and bonsai tree care.",
            "goal_title": "Phân tích dữ liệu tài chính bằng Python Pandas",
            "learner_level": "INTERMEDIATE",
            "milestones": [
                {
                    "milestone_id": "m1",
                    "sequence_order": 1,
                    "title": "Chặng 1: Làm sạch chuỗi thời gian & Tính chỉ số tài chính với Pandas",
                    "learning_outcomes": [
                        "M1-O1: Xử lý dữ liệu thiếu, resample chuỗi thời gian OHLCV bằng Pandas",
                        "M1-O2: Tính lợi suất, độ biến động và drawdown danh mục đầu tư",
                    ],
                    "completion_criteria": "Xuất báo cáo hiệu suất danh mục từ file CSV lịch sử giá cổ phiếu.",
                }
            ],
            "proposal_data": {
                "tasks": [
                    {
                        "task_id": "T1",
                        "milestone_id": "m1",
                        "title": "Lý thuyết luyện phát âm tiếng Pháp cơ bản: bảng chữ cái và nguyên âm mũi",
                        "task_type": "THEORY",
                        "estimated_minutes": 45,
                        "learning_objective": "Phát âm chuẩn 4 nguyên âm mũi tiếng Pháp.",
                        "completion_criteria": "Đọc đúng 20 từ vựng tiếng Pháp cơ bản trong bản ghi âm.",
                        "covered_outcome_ids": ["M1-O1"],
                        "depends_on_task_ids": [],
                    },
                    {
                        "task_id": "T2",
                        "milestone_id": "m1",
                        "title": "Thực hành chà nhám gỗ sồi và sơn phủ PU 3 lớp chống ẩm",
                        "task_type": "PRACTICE",
                        "estimated_minutes": 60,
                        "learning_objective": "Hoàn thiện bề mặt gỗ mịn không bọt khí.",
                        "completion_criteria": "Tấm gỗ có độ bóng đều và khô hoàn toàn sau 3 lớp sơn.",
                        "covered_outcome_ids": ["M1-O2"],
                        "depends_on_task_ids": ["T1"],
                    },
                    {
                        "task_id": "T3",
                        "milestone_id": "m1",
                        "title": "Dự án uốn dây kẽm tạo dáng và cắt tỉa rễ cây bonsai trong nhà",
                        "task_type": "PROJECT",
                        "estimated_minutes": 60,
                        "learning_objective": "Tạo dáng trực lắc cho cây sanh mini.",
                        "completion_criteria": "Cây bonsai được thay chậu thoát nước tốt và định hình tán cân đối.",
                        "covered_outcome_ids": ["M1-O1", "M1-O2"],
                        "depends_on_task_ids": ["T2"],
                    },
                ],
                "dependencies": [
                    {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
                    {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
                ],
            },
        }
    )

    assert len(cases) == 16, f"Expected 16 bad proposals, got {len(cases)}"
    return cases


async def run_judge_single_case(
    *,
    case: dict[str, Any],
    arm_name: str,
    thinking_level: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    adapter = _TelemetryAdapter()
    t0 = time.perf_counter()
    outcome = await execute_tier3_pedagogical_judge(
        adapter,
        case["proposal_data"],
        enable_tier3_judge=True,
        tier3_timeout_seconds=timeout_seconds,
        min_judge_remaining_seconds=1.0,
        thinking_level=thinking_level,
        goal_title=case["goal_title"],
        learner_level=case["learner_level"],
        milestones_metadata=case["milestones"],
    )
    wall_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    last_call = adapter.calls[-1] if adapter.calls else {}
    raw_payload = last_call.get("payload") if isinstance(last_call.get("payload"), dict) else {}
    raw_issues = raw_payload.get("issues", []) if isinstance(raw_payload, dict) else []
    caught = outcome.judge_status in {"NEEDS_REVIEW", "FAIL"}

    return {
        "case_id": case["case_id"],
        "error_group": case["error_group"],
        "arm": arm_name,
        "thinking_level": thinking_level,
        "timeout_seconds": timeout_seconds,
        "actual_model_id": last_call.get("model_id"),
        "wall_ms": wall_ms,
        "exceeded_8s": wall_ms > 8000.0,
        "judge_skipped": outcome.judge_skipped,
        "judge_status": outcome.judge_status,
        "caught_as_bad": caught,
        "pedagogical_score": outcome.pedagogical_score,
        "advisory_warnings": outcome.advisory_warnings,
        "raw_issues": raw_issues,
        "unsupported_issues_filtered": outcome.unsupported_issues_filtered,
        "prompt_tokens": outcome.prompt_tokens,
        "completion_tokens": outcome.completion_tokens,
        "thinking_tokens": outcome.thinking_tokens,
        "call_error": last_call.get("error_message") if not last_call.get("ok") else None,
    }


def _summarize_judge_calibration(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    caught_count = sum(1 for r in results if r["caught_as_bad"])
    passed_false_neg = [r for r in results if r["judge_status"] == "PASSED"]
    pending_count = sum(1 for r in results if r["judge_status"] == "REVIEW_PENDING")
    scores = [float(r["pedagogical_score"]) for r in results if r["pedagogical_score"] is not None]
    latencies = [float(r["wall_ms"]) for r in results]
    over_8s = [r for r in results if r["exceeded_8s"]]

    by_group: dict[str, Any] = {}
    for grp in sorted({r["error_group"] for r in results}):
        grp_rows = [r for r in results if r["error_group"] == grp]
        grp_caught = sum(1 for r in grp_rows if r["caught_as_bad"])
        grp_scores = [
            float(r["pedagogical_score"]) for r in grp_rows if r["pedagogical_score"] is not None
        ]
        by_group[grp] = {
            "total": len(grp_rows),
            "caught_count": grp_caught,
            "catch_rate": round(grp_caught / max(1, len(grp_rows)), 4),
            "scores": grp_scores,
            "statuses": [r["judge_status"] for r in grp_rows],
        }

    return {
        "total_cases": total,
        "caught_count": caught_count,
        "catch_rate": round(caught_count / max(1, total), 4),
        "false_negative_passed_count": len(passed_false_neg),
        "review_pending_count": pending_count,
        "score_distribution": {
            "min": min(scores) if scores else None,
            "median": percentile(scores, 50.0) if scores else None,
            "p95": percentile(scores, 95.0) if scores else None,
            "max": max(scores) if scores else None,
            "mean": round(statistics.mean(scores), 2) if scores else None,
            "per_case_scores": [
                {
                    "case_id": r["case_id"],
                    "error_group": r["error_group"],
                    "score": r["pedagogical_score"],
                    "status": r["judge_status"],
                }
                for r in results
            ],
        },
        "latency_ms": summarize_numeric(latencies),
        "exceeded_8s_count": len(over_8s),
        "exceeded_8s_rate": round(len(over_8s) / max(1, total), 4),
        "by_error_group": by_group,
        "false_negatives": [
            {
                "case_id": r["case_id"],
                "error_group": r["error_group"],
                "pedagogical_score": r["pedagogical_score"],
                "judge_status": r["judge_status"],
                "advisory_warnings": r["advisory_warnings"],
                "raw_issues": r["raw_issues"],
            }
            for r in passed_false_neg
        ],
    }


async def run_judge_calibration_phase() -> dict[str, Any]:
    print("\n=== [Part 2B] Judge Calibration on 16 Bad Proposals (-low vs -medium) ===", flush=True)
    cases = _build_16_bad_proposals()
    arms = [
        {"arm": "judge_low", "thinking_level": "LOW", "timeout_seconds": 15.0},
        {"arm": "judge_medium", "thinking_level": "MEDIUM", "timeout_seconds": 25.0},
    ]
    per_arm_results: dict[str, list[dict[str, Any]]] = {a["arm"]: [] for a in arms}
    per_arm_summary: dict[str, Any] = {}

    for arm_cfg in arms:
        arm_name = arm_cfg["arm"]
        t_level = arm_cfg["thinking_level"]
        timeout_s = arm_cfg["timeout_seconds"]
        print(f"\n--- Running {arm_name} (thinking={t_level}, timeout={timeout_s}s) ---", flush=True)
        for idx, case in enumerate(cases, start=1):
            rec = await run_judge_single_case(
                case=case,
                arm_name=arm_name,
                thinking_level=t_level,
                timeout_seconds=timeout_s,
            )
            per_arm_results[arm_name].append(rec)
            print(
                f"[{arm_name} {idx:02d}/16] {case['case_id']} ({case['error_group']}): "
                f"status={rec['judge_status']} score={rec['pedagogical_score']} "
                f"caught={rec['caught_as_bad']} wall={rec['wall_ms']/1000:.2f}s "
                f"over8s={rec['exceeded_8s']} model={rec['actual_model_id']} "
                f"t_tok={rec['thinking_tokens']}",
                flush=True,
            )
        per_arm_summary[arm_name] = _summarize_judge_calibration(per_arm_results[arm_name])

    return {
        "bad_proposals_count": len(cases),
        "bad_proposals_catalog": [
            {
                "case_id": c["case_id"],
                "error_group": c["error_group"],
                "error_description": c["error_description"],
                "goal_title": c["goal_title"],
                "learner_level": c["learner_level"],
            }
            for c in cases
        ],
        "summary_by_arm": per_arm_summary,
        "runs_by_arm": per_arm_results,
    }


# ---------------------------------------------------------------------------
# Part 3: Pure Quality A/B (-low vs -medium) for Planner + Decomposer on 5 Goals
# ---------------------------------------------------------------------------
def _build_5_diverse_goals() -> list[dict[str, Any]]:
    return [
        {
            "goal_key": "G1_BEGINNER_PYTHON_FASTAPI",
            "goal_title": "Nền tảng Python & FastAPI cho người mới bắt đầu",
            "raw_description": (
                "Học Python cơ bản (biến, hàm, cấu trúc dữ liệu, type hints), Pydantic v2 "
                "và xây dựng REST API CRUD với FastAPI + kiểm thử pytest cơ bản trong 30 ngày."
            ),
            "learner_level": "BEGINNER",
            "generation_strategy": "FULL_SCOPE",
            "start_date": "2026-11-17",
            "target_date": "2026-12-17",
            "opt_session_minutes": 60,
            "availability": AvailabilityConfigurationDTO(
                mode="MODE_A",
                daily_quota_minutes={
                    "monday": 90,
                    "tuesday": 90,
                    "wednesday": 90,
                    "thursday": 90,
                    "friday": 90,
                    "saturday": 120,
                    "sunday": 120,
                },
                default_daily_quota_minutes=90,
                availability_slots=(),
                disabled_weekdays=frozenset(),
            ),
        },
        {
            "goal_key": "G2_INTERMEDIATE_SYSTEM_DESIGN_CACHE",
            "goal_title": "Thiết kế Hệ thống & Distributed Cache với Redis",
            "raw_description": (
                "Nắm vững các chiến lược caching (Cache-Aside, Write-Through, Write-Behind), "
                "consistent hashing, phòng chống cache stampede/avalanche, eviction policies "
                "và triển khai cụm Redis phân tán có rate limiting trong 4 tuần."
            ),
            "learner_level": "INTERMEDIATE",
            "generation_strategy": "FULL_SCOPE",
            "start_date": "2026-11-17",
            "target_date": "2026-12-15",
            "opt_session_minutes": 60,
            "availability": AvailabilityConfigurationDTO(
                mode="MODE_B",
                daily_quota_minutes={},
                default_daily_quota_minutes=120,
                availability_slots=(
                    AvailabilitySlotDTO(
                        day_of_week="tuesday",
                        start_time="19:30",
                        end_time="21:30",
                        end_day_offset=0,
                        is_active=True,
                    ),
                    AvailabilitySlotDTO(
                        day_of_week="thursday",
                        start_time="19:30",
                        end_time="21:30",
                        end_day_offset=0,
                        is_active=True,
                    ),
                    AvailabilitySlotDTO(
                        day_of_week="saturday",
                        start_time="09:00",
                        end_time="12:00",
                        end_day_offset=0,
                        is_active=True,
                    ),
                ),
                disabled_weekdays=frozenset(),
            ),
        },
        {
            "goal_key": "G3_ADVANCED_RUST_ASYNC_TOKIO",
            "goal_title": "Rust Async Programming & Tokio Runtime chuyên sâu",
            "raw_description": (
                "Làm chủ Future trait, Pin/Unpin, Waker, Tokio work-stealing scheduler, "
                "channels, backpressure, graceful shutdown và tối ưu lock-free concurrency "
                "cho network service hiệu năng cao trong 6 tuần."
            ),
            "learner_level": "ADVANCED",
            "generation_strategy": "FULL_SCOPE",
            "start_date": "2026-11-17",
            "target_date": "2026-12-29",
            "opt_session_minutes": 90,
            "availability": AvailabilityConfigurationDTO(
                mode="MODE_A",
                daily_quota_minutes={
                    "monday": 90,
                    "tuesday": 90,
                    "wednesday": 90,
                    "thursday": 90,
                    "friday": 90,
                    "saturday": 150,
                    "sunday": 150,
                },
                default_daily_quota_minutes=90,
                availability_slots=(),
                disabled_weekdays=frozenset(),
            ),
        },
        {
            "goal_key": "G4_BEGINNER_IELTS_WRITING",
            "goal_title": "IELTS Academic Writing Task 1 & Task 2 từ nền tảng",
            "raw_description": (
                "Người mới bắt đầu luyện viết IELTS Academic mục tiêu 6.5: nắm cấu trúc câu "
                "học thuật, mô tả biểu đồ Task 1 (line, bar, table, process) và lập luận "
                "Task 2 (opinion, discussion, problem-solution) kèm tự chấm theo 4 tiêu chí."
            ),
            "learner_level": "BEGINNER",
            "generation_strategy": "FULL_SCOPE",
            "start_date": "2026-11-17",
            "target_date": "2026-12-31",
            "opt_session_minutes": 60,
            "availability": AvailabilityConfigurationDTO(
                mode="MODE_A",
                daily_quota_minutes={
                    "monday": 60,
                    "tuesday": 60,
                    "wednesday": 60,
                    "thursday": 60,
                    "friday": 60,
                    "saturday": 90,
                    "sunday": 90,
                },
                default_daily_quota_minutes=60,
                availability_slots=(),
                disabled_weekdays=frozenset(),
            ),
        },
        {
            "goal_key": "G5_INTERMEDIATE_DATA_ENG_AIRFLOW_DBT",
            "goal_title": "Data Engineering thực chiến với Apache Airflow & dbt",
            "raw_description": (
                "Xây dựng pipeline ELT hiện đại: thiết kế DAG Airflow idempotent (XCom, "
                "TaskFlow API, retry/SLA), mô hình hóa dữ liệu staging/mart với dbt "
                "(tests, snapshots, incremental models) và kiểm soát chất lượng dữ liệu."
            ),
            "learner_level": "INTERMEDIATE",
            "generation_strategy": "FULL_SCOPE",
            "start_date": "2026-11-17",
            "target_date": "2026-12-22",
            "opt_session_minutes": 60,
            "availability": AvailabilityConfigurationDTO(
                mode="MODE_B",
                daily_quota_minutes={},
                default_daily_quota_minutes=90,
                availability_slots=(
                    AvailabilitySlotDTO(
                        day_of_week="monday",
                        start_time="19:30",
                        end_time="21:00",
                        end_day_offset=0,
                        is_active=True,
                    ),
                    AvailabilitySlotDTO(
                        day_of_week="wednesday",
                        start_time="19:30",
                        end_time="21:00",
                        end_day_offset=0,
                        is_active=True,
                    ),
                    AvailabilitySlotDTO(
                        day_of_week="friday",
                        start_time="19:30",
                        end_time="21:00",
                        end_day_offset=0,
                        is_active=True,
                    ),
                    AvailabilitySlotDTO(
                        day_of_week="saturday",
                        start_time="09:00",
                        end_time="12:00",
                        end_day_offset=0,
                        is_active=True,
                    ),
                ),
                disabled_weekdays=frozenset(),
            ),
        },
    ]


def _build_decomposer_user_prompt(
    *,
    goal: dict[str, Any],
    milestones: list[Milestone],
) -> str:
    avail_config: AvailabilityConfigurationDTO = goal["availability"]
    sanitized_title = format_untrusted_block(UntrustedBlockKind.GOAL_TITLE, goal["goal_title"])
    sanitized_desc = format_untrusted_block(
        UntrustedBlockKind.GOAL_RAW_DESCRIPTION, goal["raw_description"]
    )
    milestone_lines = [
        (
            f"- id={m.id} | seq={m.sequence_order} | "
            f"title={format_untrusted_block(UntrustedBlockKind.MILESTONE_DATA, m.title)} | "
            f"outcome_ids={','.join(f'M{m.sequence_order}-O{i}' for i in range(1, len(m.learning_outcomes) + 1))} | "
            f"required_concepts={','.join(m.required_concepts)} | "
            f"estimated_effort_minutes={m.estimated_effort_minutes}"
        )
        for m in milestones
    ]
    slot_lines = [
        f"{slot.day_of_week}: {slot.start_time}-{slot.end_time}"
        for slot in avail_config.availability_slots
        if slot.is_active
    ]
    if not slot_lines and avail_config.mode == "MODE_A":
        slot_lines = [
            f"{day}: quota={mins}m"
            for day, mins in avail_config.daily_quota_minutes.items()
        ]
    header_markers = (
        "GENERATE_PROPOSAL_TASKS\n"
        f"Start Date: {goal['start_date']}\n"
        f"Target Date: {goal['target_date']}\n"
        "MILESTONE_IDS:\n"
        + "\n".join(milestone_lines)
        + "\nAVAILABILITY_SLOTS:\n"
        + ("\n".join(slot_lines) if slot_lines else "monday: 19:30-21:30")
    )

    milestone_details = [
        {
            "milestone_id": str(m.id),
            "sequence_order": m.sequence_order,
            "title": m.title,
            "learning_outcomes": [
                {"id": f"M{m.sequence_order}-O{i}", "description": out}
                for i, out in enumerate(m.learning_outcomes, start=1)
            ],
            "completion_criteria": m.completion_criteria or "",
            "estimated_effort_minutes": m.estimated_effort_minutes,
            "required_concepts": list(m.required_concepts),
            "unverified_concepts": list(m.unverified_concepts),
        }
        for m in milestones
    ]

    structured_ctx = (
        f"Roadmap: {sanitized_title}\n"
        f"Description: {sanitized_desc}\n"
        f"Prior Knowledge Level: {sanitize_untrusted_text(goal['learner_level'])}\n"
        f"Availability Mode: {avail_config.mode}\n"
        f"Learner Optimal Session Minutes: {goal['opt_session_minutes']}\n"
        f"Milestones Metadata:\n{json.dumps(milestone_details, ensure_ascii=False)}"
    )
    return build_task_decomposer_prompt(f"{header_markers}\n\n{structured_ctx}")


async def run_single_roadmap_arm(
    *,
    goal: dict[str, Any],
    arm_key: str,
    thinking_level: str,
) -> dict[str, Any]:
    planning_reg = build_planning_prompt_registry()
    planner_tpl = planning_reg.latest(MILESTONE_PLANNER_SKILL.skill_id)
    decomposer_tpl = planning_reg.latest(TASK_DECOMPOSER_SKILL.skill_id)
    kb = InMemoryKnowledgeBaseRepository()

    # ----- Step 1: Milestone Planner -----
    planner_dispatcher = KnowledgeToolDispatcher(
        kb,
        stage=RoadmapPipelineStage.MILESTONE_PLANNING,
        max_tool_calls=2,
        timeout_seconds=10.0,
    )
    planner_context = "\n".join(
        [
            f"Tiêu đề mục tiêu: {format_untrusted_block(UntrustedBlockKind.GOAL_TITLE, goal['goal_title'])}",
            f"Mô tả chi tiết: {format_untrusted_block(UntrustedBlockKind.GOAL_RAW_DESCRIPTION, goal['raw_description'])}",
            f"Trình độ đầu vào: {goal['learner_level']}",
            f"Ngày bắt đầu: {goal['start_date']}",
            f"Ngày đích: {goal['target_date']}",
            f"Thời lượng phiên tối ưu (opt_session_minutes): {goal['opt_session_minutes']} phút",
        ]
    )
    base_planner_prompt = build_milestone_planner_prompt(
        planner_context,
        generation_strategy=goal["generation_strategy"],
    )

    planner_adapter = _TelemetryAdapter()
    planner_attempts = 0
    planner_violations: list[dict[str, Any]] = []
    planner_payload: dict[str, Any] = {}
    planner_error: str | None = None
    planner_t0 = time.perf_counter()

    current_planner_prompt = base_planner_prompt
    for attempt in (1, 2):
        planner_attempts = attempt
        mgr = AIExecutionManager(
            provider=planner_adapter,
            manage_quota=False,
            max_retries=0,
            timeout_seconds=120.0,
            tool_call_timeout_seconds=45.0,
        )
        try:
            exec_res = await mgr.execute(
                user_id=uuid4(),
                operation_type="MILESTONE_GEN_AB",
                system_prompt=planner_tpl.system_template,
                user_prompt=current_planner_prompt,
                response_schema=MilestoneGenerationLLMOutput,
                tools=(
                    planner_dispatcher.get_allowed_tool_declarations()
                    if attempt == 1
                    else None
                ),
                tool_executor=planner_dispatcher.dispatch if attempt == 1 else None,
                max_tool_calls=2 if attempt == 1 else 0,
                thinking_level=thinking_level,
                prompt_template=planner_tpl,
            )
            planner_payload = (
                exec_res.value.model_dump()
                if hasattr(exec_res.value, "model_dump")
                else dict(exec_res.value)
            )
            raw_ms = planner_payload.get("milestones", [])
            violations = ProposalValidationGateOrchestrator.validate_ai_milestones_tier1(raw_ms)
            planner_violations = [v.to_dict() for v in violations]
            if not violations:
                planner_error = None
                break
            if attempt == 1:
                current_planner_prompt = ProposalValidationGateOrchestrator.build_self_correction_prompt(
                    base_planner_prompt,
                    violations,
                    attempt_number=1,
                )
        except Exception as exc:
            planner_error = sanitize_error_message(exc)
            break

    planner_wall_ms = round((time.perf_counter() - planner_t0) * 1000.0, 2)
    planner_prompt_tokens = sum(c.get("prompt_tokens", 0) for c in planner_adapter.calls if c.get("ok"))
    planner_output_tokens = sum(c.get("output_tokens", 0) for c in planner_adapter.calls if c.get("ok"))
    planner_thinking_tokens = sum(c.get("thinking_tokens", 0) for c in planner_adapter.calls if c.get("ok"))
    planner_model_id = next(
        (c.get("model_id") for c in reversed(planner_adapter.calls) if c.get("ok")),
        None,
    )

    raw_milestones = planner_payload.get("milestones", []) if isinstance(planner_payload, dict) else []
    roadmap_id = generate_uuid7()
    milestone_entities: list[Milestone] = []
    if raw_milestones and not planner_error:
        try:
            for item in sorted(raw_milestones, key=lambda m: int(m.get("sequence_order", 1))):
                m_entity = Milestone(
                    id=generate_uuid7(),
                    roadmap_id=roadmap_id,
                    sequence_order=int(item.get("sequence_order", 1)),
                    title=str(item.get("title", "")).strip(),
                    description=str(item.get("description", "")).strip() or None,
                    learning_outcomes=tuple(
                        str(o).strip() for o in (item.get("learning_outcomes") or []) if str(o).strip()
                    ),
                    completion_criteria=str(item.get("completion_criteria", "")).strip() or None,
                    estimated_effort_minutes=max(15, int(item.get("estimated_effort_minutes", 60) or 60)),
                    required_concepts=tuple(
                        str(c).strip() for c in (item.get("required_concepts") or []) if str(c).strip()
                    ),
                    unverified_concepts=tuple(
                        str(c).strip() for c in (item.get("unverified_concepts") or []) if str(c).strip()
                    ),
                    status=MilestoneStatus.APPROVED,
                )
                milestone_entities.append(m_entity)
        except Exception as exc:
            planner_error = f"MilestoneEntityError: {sanitize_error_message(exc)}"

    milestones_serialized = [
        {
            "milestone_id": str(m.id),
            "sequence_order": m.sequence_order,
            "title": m.title,
            "description": m.description,
            "learning_outcomes": [
                {"id": f"M{m.sequence_order}-O{i}", "description": out}
                for i, out in enumerate(m.learning_outcomes, start=1)
            ],
            "completion_criteria": m.completion_criteria,
            "estimated_effort_minutes": m.estimated_effort_minutes,
            "required_concepts": list(m.required_concepts),
            "unverified_concepts": list(m.unverified_concepts),
        }
        for m in milestone_entities
    ]

    # ----- Step 2: Task Decomposer + Tier 1 & Tier 2 Validation Gate (max 1 retry) -----
    decomp_wall_ms = 0.0
    decomp_attempts_used = 0
    decomp_tier1_2_passed = False
    decomp_error: str | None = None
    decomp_gate_violations: list[dict[str, Any]] = []
    decomp_retry_history: list[dict[str, Any]] = []
    decomp_soft_warnings: list[Any] = []
    validated_proposal: dict[str, Any] = {}
    decomp_adapter = _TelemetryAdapter()
    decomp_dispatcher = KnowledgeToolDispatcher(
        kb,
        stage=RoadmapPipelineStage.TASK_DECOMPOSITION,
        max_tool_calls=2,
        timeout_seconds=10.0,
    )

    if milestone_entities:
        decomp_user_prompt = _build_decomposer_user_prompt(
            goal=goal,
            milestones=milestone_entities,
        )
        milestone_summary_json = json.dumps(
            [
                {
                    "milestone_id": str(m.id),
                    "sequence_order": m.sequence_order,
                    "title": m.title,
                    "learning_outcomes": list(m.learning_outcomes),
                    "completion_criteria": m.completion_criteria or "",
                    "estimated_effort_minutes": m.estimated_effort_minutes,
                    "required_concepts": list(m.required_concepts),
                }
                for m in milestone_entities
            ],
            ensure_ascii=False,
        )
        orchestrator = ProposalValidationGateOrchestrator(
            llm_provider=decomp_adapter,
            enable_tier3_judge=False,
            roadmap_id=roadmap_id,
        )
        decomp_t0 = time.perf_counter()
        try:
            gate_res = await orchestrator.generate_and_validate_proposal_with_retry(
                system_prompt=decomposer_tpl.system_template,
                user_prompt=decomp_user_prompt,
                response_schema=TaskProposalLLMOutput.model_json_schema(),
                availability=goal["availability"],
                valid_milestone_ids={m.id for m in milestone_entities},
                current_roadmap_target_date=date.fromisoformat(goal["target_date"]),
                goal_title=goal["goal_title"],
                learner_level=goal["learner_level"],
                milestone_summary=milestone_summary_json,
                max_retries=1,
                start_date=date.fromisoformat(goal["start_date"]),
                milestone_order_map={str(m.id): m.sequence_order for m in milestone_entities},
                tools=decomp_dispatcher.get_allowed_tool_declarations(),
                tool_executor=decomp_dispatcher.dispatch,
                max_tool_calls=2,
                thinking_level=thinking_level,
                deterministic_allocation=True,
                preferred_session_minutes=goal["opt_session_minutes"],
                milestones=milestone_entities,
                resource_resolver=lambda raw_prop: resolve_task_resources_from_tool_results(
                    raw_prop,
                    decomp_dispatcher.collected_resources,
                    strict=True,
                ),
                prompt_template=decomposer_tpl,
            )
            decomp_tier1_2_passed = gate_res.is_valid
            decomp_attempts_used = gate_res.attempts_used
            decomp_retry_history = list(gate_res.retry_history)
            decomp_soft_warnings = [
                w.to_dict() if hasattr(w, "to_dict") else str(w)
                for w in (getattr(gate_res, "soft_overflow_warnings", None) or ())
            ]
            validated_proposal = dict(gate_res.validated_proposal_data or {})
        except ProposalValidationGateError as exc:
            decomp_error = f"{exc.code}: {exc.message}"
            decomp_gate_violations = list(exc.violations)
            decomp_attempts_used = len([c for c in decomp_adapter.calls if c.get("ok")])
            last_ok = next((c for c in reversed(decomp_adapter.calls) if c.get("ok")), None)
            if last_ok and isinstance(last_ok.get("payload"), dict):
                validated_proposal = dict(last_ok["payload"])
        except Exception as exc:
            decomp_error = sanitize_error_message(exc)
            decomp_attempts_used = len(decomp_adapter.calls)
        decomp_wall_ms = round((time.perf_counter() - decomp_t0) * 1000.0, 2)

    decomp_prompt_tokens = sum(c.get("prompt_tokens", 0) for c in decomp_adapter.calls if c.get("ok"))
    decomp_output_tokens = sum(c.get("output_tokens", 0) for c in decomp_adapter.calls if c.get("ok"))
    decomp_thinking_tokens = sum(c.get("thinking_tokens", 0) for c in decomp_adapter.calls if c.get("ok"))
    decomp_model_id = next(
        (c.get("model_id") for c in reversed(decomp_adapter.calls) if c.get("ok")),
        None,
    )

    # ----- Step 3: Evaluate resulting roadmap with Calibrated Judge (-low and -medium) -----
    judge_evaluations: dict[str, Any] = {}
    tasks_list = validated_proposal.get("tasks", []) if isinstance(validated_proposal, dict) else []
    if tasks_list and milestone_entities:
        for j_arm, j_level, j_timeout in (
            ("judge_low", "LOW", 15.0),
            ("judge_medium", "MEDIUM", 25.0),
        ):
            j_adapter = _TelemetryAdapter()
            j_t0 = time.perf_counter()
            j_outcome = await execute_tier3_pedagogical_judge(
                j_adapter,
                validated_proposal,
                enable_tier3_judge=True,
                tier3_timeout_seconds=j_timeout,
                min_judge_remaining_seconds=1.0,
                thinking_level=j_level,
                goal_title=goal["goal_title"],
                learner_level=goal["learner_level"],
                milestones_metadata=milestone_entities,
            )
            j_wall_ms = round((time.perf_counter() - j_t0) * 1000.0, 2)
            j_call = j_adapter.calls[-1] if j_adapter.calls else {}
            j_payload = j_call.get("payload") if isinstance(j_call.get("payload"), dict) else {}
            judge_evaluations[j_arm] = {
                "actual_model_id": j_call.get("model_id"),
                "wall_ms": j_wall_ms,
                "judge_skipped": j_outcome.judge_skipped,
                "judge_status": j_outcome.judge_status,
                "pedagogical_score": j_outcome.pedagogical_score,
                "advisory_warnings": j_outcome.advisory_warnings,
                "raw_issues": j_payload.get("issues", []) if isinstance(j_payload, dict) else [],
                "prompt_tokens": j_outcome.prompt_tokens,
                "completion_tokens": j_outcome.completion_tokens,
                "thinking_tokens": j_outcome.thinking_tokens,
            }

    return {
        "goal_key": goal["goal_key"],
        "goal_title": goal["goal_title"],
        "learner_level": goal["learner_level"],
        "arm": arm_key,
        "thinking_level": thinking_level,
        "planner": {
            "ok": planner_error is None and len(milestone_entities) > 0,
            "error": planner_error,
            "attempts": planner_attempts,
            "tier1_violations": planner_violations,
            "tool_calls_count": planner_dispatcher.call_count,
            "tool_calls": [
                {"tool_name": tc.tool_name, "arguments": tc.arguments}
                for tc in planner_dispatcher.call_history
            ],
            "wall_ms": planner_wall_ms,
            "model_id": planner_model_id,
            "prompt_tokens": planner_prompt_tokens,
            "output_tokens": planner_output_tokens,
            "thinking_tokens": planner_thinking_tokens,
            "scope_summary": planner_payload.get("scope_summary", "") if isinstance(planner_payload, dict) else "",
            "deferred_scope": planner_payload.get("deferred_scope", []) if isinstance(planner_payload, dict) else [],
            "milestones_count": len(milestones_serialized),
            "milestones": milestones_serialized,
        },
        "decomposer": {
            "tier1_2_passed": decomp_tier1_2_passed,
            "error": decomp_error,
            "attempts_used": decomp_attempts_used,
            "gate_violations": decomp_gate_violations,
            "retry_history": decomp_retry_history,
            "soft_warnings": decomp_soft_warnings,
            "tool_calls_count": decomp_dispatcher.call_count,
            "tool_calls": [
                {"tool_name": tc.tool_name, "arguments": tc.arguments}
                for tc in decomp_dispatcher.call_history
            ],
            "wall_ms": decomp_wall_ms,
            "model_id": decomp_model_id,
            "prompt_tokens": decomp_prompt_tokens,
            "output_tokens": decomp_output_tokens,
            "thinking_tokens": decomp_thinking_tokens,
            "tasks_count": len(tasks_list),
            "dependencies_count": len(validated_proposal.get("dependencies", []) or [])
            if isinstance(validated_proposal, dict)
            else 0,
            "total_estimated_minutes": sum(
                int(t.get("estimated_minutes", 0) or 0)
                for t in tasks_list
                if isinstance(t, dict)
            ),
            "task_type_counts": dict(
                Counter(str(t.get("task_type", "UNKNOWN")) for t in tasks_list if isinstance(t, dict))
            ),
            "proposal": validated_proposal,
        },
        "judge_evaluations": judge_evaluations,
    }


def _summarize_quality_ab(roadmaps: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for arm_key in ("low", "medium"):
        arm_rows = [r for r in roadmaps if r["arm"] == arm_key]
        planner_ok = sum(1 for r in arm_rows if r["planner"]["ok"])
        decomp_ok = sum(1 for r in arm_rows if r["decomposer"]["tier1_2_passed"])
        planner_lat = [r["planner"]["wall_ms"] for r in arm_rows]
        decomp_lat = [r["decomposer"]["wall_ms"] for r in arm_rows]
        ms_counts = [r["planner"]["milestones_count"] for r in arm_rows]
        task_counts = [r["decomposer"]["tasks_count"] for r in arm_rows]
        j_low_scores = [
            float(r["judge_evaluations"]["judge_low"]["pedagogical_score"])
            for r in arm_rows
            if r["judge_evaluations"].get("judge_low", {}).get("pedagogical_score") is not None
        ]
        j_med_scores = [
            float(r["judge_evaluations"]["judge_medium"]["pedagogical_score"])
            for r in arm_rows
            if r["judge_evaluations"].get("judge_medium", {}).get("pedagogical_score") is not None
        ]
        summary[arm_key] = {
            "total_goals": len(arm_rows),
            "planner_ok_count": planner_ok,
            "decomposer_tier1_2_passed_count": decomp_ok,
            "planner_wall_ms": summarize_numeric(planner_lat),
            "decomposer_wall_ms": summarize_numeric(decomp_lat),
            "avg_milestones": round(statistics.mean(ms_counts), 2) if ms_counts else 0.0,
            "avg_tasks": round(statistics.mean(task_counts), 2) if task_counts else 0.0,
            "planner_thinking_tokens_total": sum(r["planner"]["thinking_tokens"] for r in arm_rows),
            "decomposer_thinking_tokens_total": sum(r["decomposer"]["thinking_tokens"] for r in arm_rows),
            "judge_low_scores": j_low_scores,
            "judge_low_mean": round(statistics.mean(j_low_scores), 2) if j_low_scores else None,
            "judge_medium_scores": j_med_scores,
            "judge_medium_mean": round(statistics.mean(j_med_scores), 2) if j_med_scores else None,
        }
    return summary


async def run_quality_ab_phase() -> dict[str, Any]:
    print("\n=== [Part 3] Pure Quality A/B (-low vs -medium) on 5 Goals (10 Roadmaps) ===", flush=True)
    goals = _build_5_diverse_goals()
    roadmaps: list[dict[str, Any]] = []

    for g_idx, goal in enumerate(goals, start=1):
        for arm_key, thinking_level in (("low", "LOW"), ("medium", "MEDIUM")):
            print(
                f"\n--- Goal {g_idx}/5 [{goal['goal_key']}] Arm={arm_key} ({thinking_level}) ---",
                flush=True,
            )
            rm = await run_single_roadmap_arm(
                goal=goal,
                arm_key=arm_key,
                thinking_level=thinking_level,
            )
            roadmaps.append(rm)
            j_low = rm["judge_evaluations"].get("judge_low", {})
            j_med = rm["judge_evaluations"].get("judge_medium", {})
            print(
                f"  -> planner_ok={rm['planner']['ok']} (ms={rm['planner']['milestones_count']}, "
                f"wall={rm['planner']['wall_ms']/1000:.2f}s, t_tok={rm['planner']['thinking_tokens']}) | "
                f"decomp_pass={rm['decomposer']['tier1_2_passed']} (tasks={rm['decomposer']['tasks_count']}, "
                f"att={rm['decomposer']['attempts_used']}, wall={rm['decomposer']['wall_ms']/1000:.2f}s, "
                f"t_tok={rm['decomposer']['thinking_tokens']}) | "
                f"judge_low={j_low.get('pedagogical_score')}/{j_low.get('judge_status')} | "
                f"judge_med={j_med.get('pedagogical_score')}/{j_med.get('judge_status')}",
                flush=True,
            )

    return {
        "goals_count": len(goals),
        "roadmaps_count": len(roadmaps),
        "timeout_budget_seconds": 120.0,
        "summary_by_arm": _summarize_quality_ab(roadmaps),
        "roadmaps": roadmaps,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Exp 0.9: Capability Probe, Judge Calibration & Quality A/B")
    parser.add_argument(
        "--part",
        choices=("all", "probe", "judge", "ab"),
        default="all",
        help="Run all parts or a specific part",
    )
    args = parser.parse_args()

    base_url, api_key = get_cobhub_config()
    _configure_env(base_url, api_key)

    out_file = EXPERIMENTS_OUT_DIR / OUTPUT_FILENAME
    if args.part != "all" and out_file.exists():
        existing = json.loads(out_file.read_text(encoding="utf-8"))
        existing["timestamp"] = utc_timestamp()
        existing["gateway_base_url"] = base_url
        report = existing
    else:
        report = {
            "schema_version": "1.0",
            "experiment": "exp_09_judge_and_quality_ab",
            "timestamp": utc_timestamp(),
            "gateway_base_url": base_url,
        }

    if args.part in ("all", "probe"):
        report["part_1_live_capability_probe"] = await run_live_capability_probe(base_url)

    if args.part in ("all", "judge"):
        report["part_2a_eval_54_runs_distribution"] = analyze_54_eval_runs()
        report["part_2b_judge_calibration_16_bad"] = await run_judge_calibration_phase()

    if args.part in ("all", "ab"):
        report["part_3_quality_ab_low_vs_medium"] = await run_quality_ab_phase()

    out_path = write_experiment_json(OUTPUT_FILENAME, report)
    print(f"\nSaved full Exp 0.9 report to {out_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
