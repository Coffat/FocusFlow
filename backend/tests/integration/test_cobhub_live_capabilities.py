"""Live opt-in capability checks against the cobhub LLM gateway (Nhóm 1)."""

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field

from src.evaluation.application.dtos.intelligence import ProveQuestionsLLMOutput
from src.evaluation.application.prompts import (
    PROVE_QUESTION_GENERATOR_PROMPT,
    build_prove_question_prompt,
)
from src.planning.application.dtos.planning_dtos import (
    ClarificationFollowupLLMOutput,
    CriticQualityLLMOutput,
)
from src.planning.application.services.roadmap_skills import (
    COVERAGE_PREREQUISITE_CRITIC_PROMPT,
    GOAL_CLARIFIER_FOLLOWUP_PROMPT,
    build_goal_clarifier_followup_prompt,
)
from src.shared_kernel.application.harness.execution_manager import AIExecutionManager
from src.shared_kernel.application.llm_port import LLMToolDeclarationDTO, classify_ai_error
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import LiteLLMAdapter


class _LiveSampleMilestoneItem(BaseModel):
    sequence_order: int = Field(ge=1)
    title: str
    description: str


class _LiveSampleRoadmapOutput(BaseModel):
    status: str
    summary: str
    milestones: list[_LiveSampleMilestoneItem] = Field(min_length=1)


@pytest.mark.asyncio
@pytest.mark.live_cobhub
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_GEMINI_SDK_TEST") != "1",
    reason="Opt-in live cobhub capability test (set RUN_LIVE_GEMINI_SDK_TEST=1)",
)
async def test_live_cobhub_gateway_capabilities() -> None:
    """Verify >= 4/5 schema-valid pass rate across 5 consecutive calls per capability on cobhub."""
    adapter = LiteLLMAdapter()
    if not adapter.supports_native_structured_output:
        pytest.skip("Configured provider is not native Gemini")

    async def _echo_concept_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "tool": name,
            "args": args,
            "concepts": [
                {"concept_id": "py-syntax-variables", "title": "Python Syntax & Variables"},
                {"concept_id": "py-async-io", "title": "AsyncIO Fundamentals"},
            ],
        }

    search_tool = LLMToolDeclarationDTO(
        name="search_learning_concepts",
        description="Search verified concepts from the FocusFlow catalog.",
        parameters_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    )

    critic_user_prompt = (
        "learner_level: BEGINNER\n"
        "milestone_summary: M1 - Nền tảng Python & FastAPI\n"
        '[PAYLOAD]\n{"tasks": ['
        '{"task_id": "T1", "title": "Đọc tài liệu biến & hàm Python", "task_type": "THEORY", "estimated_minutes": 45, "covered_outcome_ids": ["M1-O1"]},'
        '{"task_id": "T2", "title": "Thực hành viết 5 hàm xử lý danh sách", "task_type": "PRACTICE", "estimated_minutes": 60, "covered_outcome_ids": ["M1-O1"]}'
        '], "dependencies": [{"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": true}]}'
    )
    prove_user_prompt = build_prove_question_prompt(
        milestone_title="Cột mốc 1: FastAPI & Pydantic Validation",
        description="Thiết kế REST API chuẩn Pydantic v2 và Dependency Injection.",
        learning_outcomes=[
            "M1-O1: Phân biệt schema request/response với domain model",
            "M1-O2: Xử lý validation error và HTTP status code chuẩn",
        ],
        completion_criteria="Xây dựng được 3 endpoint CRUD có unit test.",
        required_concepts=["fastapi-routing", "pydantic-v2-models"],
        task_titles=["T1: Pydantic v2 Schema", "T2: FastAPI Router & Depends"],
    )
    followup_user_prompt = build_goal_clarifier_followup_prompt(
        gap={
            "dimension": "TIMELINE",
            "status": "PARTIAL",
            "priority": 90,
            "reason": "Người học chưa nêu rõ tuần nào cần thi hoặc hoàn thành dự án.",
        },
        prior_answers=[
            {
                "question_id": "q1",
                "answer": "Đã biết Python cơ bản, muốn làm backend FastAPI.",
            }
        ],
    )

    cases: list[dict[str, Any]] = [
        {
            "name": "SampleRoadmapOutput(tool->JSON)",
            "system_prompt": "Call search_learning_concepts once, then return valid roadmap JSON.",
            "user_prompt": "Create a 2-milestone Python learning roadmap.",
            "response_schema": _LiveSampleRoadmapOutput,
            "tools": [search_tool],
            "tool_executor": _echo_concept_tool,
            "max_tool_calls": 2,
            "thinking_level": "LOW",
        },
        {
            "name": "critic(CriticQualityLLMOutput)",
            "system_prompt": COVERAGE_PREREQUISITE_CRITIC_PROMPT.system_instruction,
            "user_prompt": critic_user_prompt,
            "response_schema": CriticQualityLLMOutput,
            "tools": None,
            "tool_executor": None,
            "max_tool_calls": 0,
            "thinking_level": "LOW",
        },
        {
            "name": "prove-question-generator(ProveQuestionsLLMOutput)",
            "system_prompt": PROVE_QUESTION_GENERATOR_PROMPT.system_instruction,
            "user_prompt": prove_user_prompt,
            "response_schema": ProveQuestionsLLMOutput,
            "tools": None,
            "tool_executor": None,
            "max_tool_calls": 0,
            "thinking_level": "LOW",
        },
        {
            "name": "goal-clarifier-followup(ClarificationFollowupLLMOutput)",
            "system_prompt": GOAL_CLARIFIER_FOLLOWUP_PROMPT.system_instruction,
            "user_prompt": followup_user_prompt,
            "response_schema": ClarificationFollowupLLMOutput,
            "tools": None,
            "tool_executor": None,
            "max_tool_calls": 0,
            "thinking_level": "LOW",
        },
    ]

    summary_lines: list[str] = []
    failures_by_case: dict[str, list[str]] = {}
    trials = 5

    for case in cases:
        passes = 0
        repairs = 0
        case_failures: list[str] = []
        for idx in range(1, trials + 1):
            manager = AIExecutionManager(provider=LiteLLMAdapter(), manage_quota=False)
            try:
                res = await manager.execute(
                    user_id=uuid4(),
                    operation_type="LIVE_COBHUB_CAPABILITY",
                    system_prompt=case["system_prompt"],
                    user_prompt=case["user_prompt"],
                    response_schema=case["response_schema"],
                    tools=case["tools"],
                    tool_executor=case["tool_executor"],
                    max_tool_calls=case["max_tool_calls"],
                    thinking_level=case["thinking_level"],
                )
                passes += 1
                repairs += res.repair_attempts
            except Exception as exc:
                cat = classify_ai_error(exc).value
                case_failures.append(f"trial#{idx}:{cat}:{type(exc).__name__}:{str(exc)[:120]}")
        failures_by_case[case["name"]] = case_failures
        summary_lines.append(
            f"[live_cobhub] {case['name']}: {passes}/{trials} (repairs={repairs}, failures={case_failures})"
        )

    for line in summary_lines:
        print(line)

    below_threshold = [
        line
        for line in summary_lines
        if ": 0/5" in line or ": 1/5" in line or ": 2/5" in line or ": 3/5" in line
    ]
    assert not below_threshold, "Capabilities below 4/5 threshold:\n" + "\n".join(summary_lines)
