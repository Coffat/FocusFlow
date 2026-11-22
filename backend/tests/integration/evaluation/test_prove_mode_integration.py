from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete, select
from uuid6 import uuid7

from src.account.infrastructure.orm.learner_memory_orm import LearnerConceptMasteryORM
from src.account.infrastructure.orm.user_orm import UserORM
from src.account.infrastructure.security.jwt_token_provider import JwtTokenProvider
from src.evaluation.application.dtos.intelligence import (
    ProveAnswerFeedbackSchema,
    ProveGradingLLMOutput,
    ProveQuestionItemSchema,
    ProveQuestionsLLMOutput,
)
from src.evaluation.presentation.deps import get_evaluation_llm_provider
from src.main import app
from src.planning.infrastructure.orm.planning_orm import GoalORM, MilestoneORM, RoadmapORM
from src.shared_kernel.application.llm_port import LLMGenerationResult
from src.shared_kernel.infrastructure.database.session import async_session_factory


class _FakeProveLLMProvider:
    @property
    def supports_native_structured_output(self) -> bool:
        return True

    async def generate_structured(
        self,
        *,
        system_prompt: str = "",
        user_prompt: str = "",
        response_schema: Any = None,
        tools: Any = None,
        tool_executor: Any = None,
        max_tool_calls: int = 2,
        thinking_level: str | None = None,
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> LLMGenerationResult:
        del (
            system_prompt,
            user_prompt,
            tools,
            tool_executor,
            max_tool_calls,
            thinking_level,
            timeout_seconds,
            tool_call_timeout_seconds,
        )
        if response_schema is ProveQuestionsLLMOutput:
            payload = ProveQuestionsLLMOutput(
                questions=[
                    ProveQuestionItemSchema(
                        id="q1",
                        prompt="Giải thích cơ chế cốt lõi của B-Tree index trong PostgreSQL.",
                    ),
                    ProveQuestionItemSchema(
                        id="q2",
                        prompt="Nêu một lỗi thường gặp khi đặt composite index sai thứ tự cột.",
                    ),
                    ProveQuestionItemSchema(
                        id="q3",
                        prompt="Vận dụng kiến thức này để tối ưu truy vấn lọc theo user_id và created_at.",
                    ),
                ]
            ).model_dump()
            return LLMGenerationResult(
                payload=payload,
                prompt_tokens=100,
                output_tokens=120,
                model_id="mock-prove-model",
            )
        if response_schema is ProveGradingLLMOutput:
            payload = ProveGradingLLMOutput(
                conceptual_understanding_score=34,
                example_grounding_score=24,
                practical_application_score=24,
                answer_evidence=[
                    ProveAnswerFeedbackSchema(
                        question_id="q1",
                        evidence="Giải thích đúng cấu trúc cây cân bằng và độ phức tạp O(log n).",
                        is_addressed=True,
                    ),
                    ProveAnswerFeedbackSchema(
                        question_id="q2",
                        evidence="Chỉ ra đúng quy tắc leftmost prefix khi đặt cột lọc.",
                        is_addressed=True,
                    ),
                    ProveAnswerFeedbackSchema(
                        question_id="q3",
                        evidence="Đề xuất đúng composite index (user_id, created_at DESC).",
                        is_addressed=True,
                    ),
                ],
                corrective_action=None,
            ).model_dump()
            return LLMGenerationResult(
                payload=payload,
                prompt_tokens=140,
                output_tokens=160,
                model_id="mock-prove-model",
            )
        raise AssertionError(f"Unexpected schema requested: {response_schema}")


async def _seed_user_and_milestone() -> tuple[UUID, UUID, UUID]:
    owner_id = uuid7()
    other_user_id = uuid7()
    goal_id = uuid7()
    roadmap_id = uuid7()
    milestone_id = uuid7()
    now = datetime.now(UTC)

    async with async_session_factory() as session:
        session.add_all(
            [
                UserORM(
                    id=owner_id,
                    email=f"prove_owner_{owner_id.hex}@focusflow.vn",
                    password_hash="argon2id$mockhash",
                    full_name="Prove Owner",
                    timezone="Asia/Ho_Chi_Minh",
                    role="LEARNER",
                    tier="FREE",
                    is_locked=False,
                ),
                UserORM(
                    id=other_user_id,
                    email=f"prove_other_{other_user_id.hex}@focusflow.vn",
                    password_hash="argon2id$mockhash",
                    full_name="Prove Other",
                    timezone="Asia/Ho_Chi_Minh",
                    role="LEARNER",
                    tier="FREE",
                    is_locked=False,
                ),
            ]
        )
        await session.flush()

        session.add(
            GoalORM(
                id=goal_id,
                user_id=owner_id,
                title="PostgreSQL Indexing Mastery",
                raw_description="Master B-Tree and composite indexes",
                status="ACTIVE",
                prior_knowledge_level="INTERMEDIATE",
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()

        session.add(
            RoadmapORM(
                id=roadmap_id,
                user_id=owner_id,
                goal_id=goal_id,
                title="PostgreSQL Indexing Roadmap",
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()

        session.add(
            MilestoneORM(
                id=milestone_id,
                roadmap_id=roadmap_id,
                sequence_order=1,
                title="B-Tree & Composite Indexes",
                description="Understand index lookup and leftmost prefix rule",
                learning_outcomes=["Explain B-Tree traversal", "Design composite indexes"],
                status="IN_PROGRESS",
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    return owner_id, other_user_id, milestone_id


async def _cleanup_users(*user_ids: UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(delete(UserORM).where(UserORM.id.in_(list(user_ids))))
        await session.commit()


@pytest.mark.asyncio
async def test_prove_mode_full_lifecycle_read_persistence_and_idor() -> None:
    owner_id, other_user_id, milestone_id = await _seed_user_and_milestone()
    owner_token = JwtTokenProvider.create_access_token(
        user_id=owner_id,
        email=f"prove_owner_{owner_id.hex}@focusflow.vn",
        role="LEARNER",
        tier="FREE",
    )
    other_token = JwtTokenProvider.create_access_token(
        user_id=other_user_id,
        email=f"prove_other_{other_user_id.hex}@focusflow.vn",
        role="LEARNER",
        tier="FREE",
    )
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}

    app.dependency_overrides[get_evaluation_llm_provider] = lambda: _FakeProveLLMProvider()
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 0. Initially no proof exists -> returns 200 with null body
            init_resp = await client.get(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/latest",
                headers=owner_headers,
            )
            assert init_resp.status_code == 200
            assert init_resp.json() is None

            # 1. Generate proof -> 202 + 3 questions
            gen_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/generate-jobs",
                headers=owner_headers,
            )
            assert gen_resp.status_code == 202
            gen_data = gen_resp.json()
            proof_id = gen_data["proof_id"]
            assert gen_data["status"] == "READY"
            assert len(gen_data["questions"]) == 3

            # 2. Reload latest proof -> restores READY state + questions
            ready_resp = await client.get(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/latest",
                headers=owner_headers,
            )
            assert ready_resp.status_code == 200
            ready_data = ready_resp.json()
            assert ready_data["id"] == proof_id
            assert ready_data["milestone_id"] == str(milestone_id)
            assert ready_data["status"] == "READY"
            assert len(ready_data["questions"]) == 3
            assert ready_data["created_at"] is not None
            assert ready_data["updated_at"] is not None

            # 3. Validation checks: invalid confidence (1.5) and empty answers -> 422
            bad_conf_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit",
                headers=owner_headers,
                json={"answers": [{"question_id": "q1", "answer": "Test"}], "confidence": 1.5},
            )
            assert bad_conf_resp.status_code == 422

            empty_ans_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit",
                headers=owner_headers,
                json={"answers": [], "confidence": 0.8},
            )
            assert empty_ans_resp.status_code == 422

            # 4. Submit proof -> 200 + score/status/feedback/mastery
            submit_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit",
                headers=owner_headers,
                json={
                    "answers": [
                        {
                            "question_id": "q1",
                            "answer": "B-Tree giữ các khóa có thứ tự, tìm kiếm O(log n).",
                        },
                        {
                            "question_id": "q2",
                            "answer": "Đặt cột range trước cột equality vi phạm leftmost prefix.",
                        },
                        {"question_id": "q3", "answer": "Tạo index (user_id, created_at DESC)."},
                    ],
                    "confidence": 0.8,
                },
            )
            assert submit_resp.status_code == 200
            submit_data = submit_resp.json()
            assert submit_data["status"] == "PASSED"
            assert submit_data["score"] == 82
            assert submit_data["is_verified"] is True
            assert submit_data["calibration_error"] == pytest.approx(-0.02, abs=1e-4)
            assert len(submit_data["answer_evidence"]) == 3

            # 5. Reload latest proof -> restores persisted PASSED result from PostgreSQL
            after_resp = await client.get(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/latest",
                headers=owner_headers,
            )
            assert after_resp.status_code == 200
            after_data = after_resp.json()
            assert after_data["id"] == proof_id
            assert after_data["milestone_id"] == str(milestone_id)
            assert after_data["status"] == "PASSED"
            assert after_data["score"] == 82
            assert after_data["confidence"] == pytest.approx(0.8, abs=1e-4)
            assert after_data["is_verified"] is True
            assert after_data["calibration_error"] == pytest.approx(-0.02, abs=1e-4)
            assert len(after_data["questions"]) == 3
            assert after_data["created_at"] is not None
            assert after_data["updated_at"] is not None

            # 6. Verify mastery persisted in PostgreSQL
            async with async_session_factory() as session:
                mastery = (
                    await session.execute(
                        select(LearnerConceptMasteryORM).where(
                            LearnerConceptMasteryORM.user_id == owner_id,
                            LearnerConceptMasteryORM.concept_key == f"milestone:{milestone_id}",
                        )
                    )
                ).scalar_one_or_none()
                assert mastery is not None
                assert float(mastery.mastery_score) == pytest.approx(0.82, abs=1e-4)

            # 7. IDOR check: other user receives 404
            idor_resp = await client.get(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/latest",
                headers=other_headers,
            )
            assert idor_resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_evaluation_llm_provider, None)
        await _cleanup_users(owner_id, other_user_id)
