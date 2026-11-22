from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete, select
from uuid6 import uuid7

from src.account.infrastructure.orm.learner_memory_orm import LearnerConceptMasteryORM
from src.account.infrastructure.orm.user_orm import (
    AIQuotaORM,
    AIQuotaReservationORM,
    AIUsageLogORM,
    UserORM,
)
from src.account.infrastructure.security.jwt_token_provider import JwtTokenProvider
from src.evaluation.application.dtos.intelligence import (
    ProveAnswerFeedbackSchema,
    ProveGradingLLMOutput,
    ProveQuestionItemSchema,
    ProveQuestionsLLMOutput,
    WeeklyReviewLLMOutput,
)
from src.evaluation.presentation.deps import get_evaluation_llm_provider
from src.main import app
from src.planning.infrastructure.orm.planning_orm import GoalORM, MilestoneORM, RoadmapORM
from src.shared_kernel.application.llm_port import LLMGenerationResult
from src.shared_kernel.infrastructure.database.session import async_session_factory


class _TrackingEvalLLMProvider:
    """Deterministic LLM double that tracks calls and supports delay / failure modes."""

    def __init__(
        self,
        *,
        fail_always: Exception | None = None,
        fail_first_n: int = 0,
        transient_error: Exception | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        self.call_count = 0
        self._fail_always = fail_always
        self._fail_first_n = fail_first_n
        self._transient_error = transient_error
        self._delay_seconds = delay_seconds

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
        self.call_count += 1
        if self._delay_seconds > 0:
            await asyncio.sleep(self._delay_seconds)
        if self._fail_always is not None:
            raise self._fail_always
        if self._fail_first_n > 0 and self.call_count <= self._fail_first_n:
            raise self._transient_error or TimeoutError("Transient LLM timeout")

        if response_schema is ProveQuestionsLLMOutput:
            payload = ProveQuestionsLLMOutput(
                questions=[
                    ProveQuestionItemSchema(id="q1", prompt="Giải thích cơ chế B-Tree index."),
                    ProveQuestionItemSchema(
                        id="q2", prompt="Nêu lỗi thường gặp với composite index."
                    ),
                    ProveQuestionItemSchema(
                        id="q3", prompt="Áp dụng tối ưu truy vấn lọc theo user_id."
                    ),
                ]
            ).model_dump()
            return LLMGenerationResult(
                payload=payload,
                prompt_tokens=110,
                output_tokens=130,
                model_id="mock-eval-model",
            )
        if response_schema is ProveGradingLLMOutput:
            payload = ProveGradingLLMOutput(
                conceptual_understanding_score=32,
                example_grounding_score=24,
                practical_application_score=24,
                answer_evidence=[
                    ProveAnswerFeedbackSchema(
                        question_id="q1",
                        evidence="Giải thích rõ cấu trúc cây cân bằng.",
                        is_addressed=True,
                    ),
                    ProveAnswerFeedbackSchema(
                        question_id="q2",
                        evidence="Nêu đúng quy tắc leftmost prefix.",
                        is_addressed=True,
                    ),
                    ProveAnswerFeedbackSchema(
                        question_id="q3",
                        evidence="Đề xuất composite index phù hợp.",
                        is_addressed=True,
                    ),
                ],
                corrective_action=None,
            ).model_dump()
            return LLMGenerationResult(
                payload=payload,
                prompt_tokens=150,
                output_tokens=170,
                model_id="mock-eval-model",
            )
        if response_schema is WeeklyReviewLLMOutput:
            payload = WeeklyReviewLLMOutput(
                strengths_feedback="Bạn đã duy trì nhịp độ học ổn định trong 7 ngày qua.",
                bottlenecks_feedback="Cần củng cố thêm các khái niệm có mức độ thành thạo thấp.",
                action_recommendations="Thực hiện 1 phiên Prove Mode để kiểm chứng kiến thức.",
            ).model_dump()
            return LLMGenerationResult(
                payload=payload,
                prompt_tokens=200,
                output_tokens=180,
                model_id="mock-eval-model",
            )
        raise AssertionError(f"Unexpected schema requested: {response_schema}")


async def _seed_eval_user(
    *,
    tier: str = "FREE",
    monthly_limit: int = 30,
    used_calls: int = 0,
    with_mastery: bool = True,
) -> tuple[UUID, UUID, UUID]:
    user_id = uuid7()
    goal_id = uuid7()
    roadmap_id = uuid7()
    milestone_id = uuid7()
    now = datetime.now(UTC)

    async with async_session_factory() as session:
        session.add(
            UserORM(
                id=user_id,
                email=f"eval_quota_{user_id.hex}@focusflow.vn",
                password_hash="argon2id$mockhash",
                full_name="Eval Quota Tester",
                timezone="Asia/Ho_Chi_Minh",
                role="LEARNER",
                tier=tier,
                is_locked=False,
            )
        )
        await session.flush()

        session.add(
            AIQuotaORM(
                id=uuid7(),
                user_id=user_id,
                monthly_limit=monthly_limit,
                used_calls=used_calls,
                reserved_calls=0,
                tokens_consumed=0,
                cycle_start=now,
                cycle_end=now + timedelta(days=30),
            )
        )
        session.add(
            GoalORM(
                id=goal_id,
                user_id=user_id,
                title="Evaluation Quota Mastery",
                raw_description="Test evaluation AI quota enforcement",
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
                goal_id=goal_id,
                user_id=user_id,
                title="Evaluation Quota Roadmap",
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
                title="B-Tree Indexing Foundations",
                description="Understand B-Tree and composite indexes",
                status="IN_PROGRESS",
                created_at=now,
                updated_at=now,
            )
        )
        if with_mastery:
            session.add(
                LearnerConceptMasteryORM(
                    id=uuid7(),
                    user_id=user_id,
                    concept_key=f"milestone:{milestone_id}",
                    mastery_score=0.75,
                    evidence_count=1,
                    last_evidence_type="PROVE_MODE",
                    updated_at=now,
                )
            )
        await session.commit()

    return user_id, roadmap_id, milestone_id


async def _cleanup_eval_user(user_id: UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(delete(AIUsageLogORM).where(AIUsageLogORM.user_id == user_id))
        await session.execute(
            delete(AIQuotaReservationORM).where(AIQuotaReservationORM.user_id == user_id)
        )
        await session.execute(delete(AIQuotaORM).where(AIQuotaORM.user_id == user_id))
        await session.execute(
            delete(LearnerConceptMasteryORM).where(LearnerConceptMasteryORM.user_id == user_id)
        )
        await session.execute(delete(UserORM).where(UserORM.id == user_id))
        await session.commit()


def _auth_headers(user_id: UUID, tier: str = "FREE") -> dict[str, str]:
    token = JwtTokenProvider().create_access_token(
        user_id=user_id,
        email=f"eval_quota_{user_id.hex}@focusflow.vn",
        role="LEARNER",
        tier=tier,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_free_tier_quota_exhausted_blocks_all_eval_ai_endpoints_without_llm_call() -> None:
    user_id, roadmap_id, milestone_id = await _seed_eval_user(
        tier="FREE",
        monthly_limit=30,
        used_calls=30,
    )
    provider = _TrackingEvalLLMProvider()
    app.dependency_overrides[get_evaluation_llm_provider] = lambda: provider
    try:
        headers = _auth_headers(user_id)
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. Prove Mode generation blocked with 429
            gen_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/generate-jobs",
                headers=headers,
            )
            assert gen_resp.status_code == 429, gen_resp.text
            assert gen_resp.json()["code"] == "QUOTA_EXHAUSTED"
            assert provider.call_count == 0

            # 2. Weekly Review generation blocked with 429
            today = date.today()
            wr_resp = await client.post(
                "/api/v1/evaluation/weekly-reviews/generate-jobs",
                headers=headers,
                json={
                    "roadmap_id": str(roadmap_id),
                    "period_start": (today - timedelta(days=6)).isoformat(),
                    "period_end": today.isoformat(),
                    "reflection": {"summary": "Tuần này học tốt."},
                },
            )
            assert wr_resp.status_code == 429, wr_resp.text
            assert wr_resp.json()["code"] == "QUOTA_EXHAUSTED"
            assert provider.call_count == 0
    finally:
        app.dependency_overrides.pop(get_evaluation_llm_provider, None)
        await _cleanup_eval_user(user_id)


@pytest.mark.asyncio
async def test_prove_gen_submit_and_weekly_review_consume_quota_and_persist_usage_logs() -> None:
    user_id, roadmap_id, milestone_id = await _seed_eval_user(
        tier="FREE",
        monthly_limit=5,
        used_calls=0,
    )
    provider = _TrackingEvalLLMProvider()
    app.dependency_overrides[get_evaluation_llm_provider] = lambda: provider
    try:
        headers = _auth_headers(user_id)
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. Prove Mode generation -> consumes 1 credit
            gen_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/generate-jobs",
                headers=headers,
            )
            assert gen_resp.status_code == 202, gen_resp.text
            proof_id = gen_resp.json()["proof_id"]

            # 2. Prove Mode submission/evaluation -> consumes 1 credit
            sub_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit",
                headers=headers,
                json={
                    "answers": [
                        {"question_id": "q1", "answer": "B-Tree giữ độ sâu cân bằng O(log n)."},
                        {
                            "question_id": "q2",
                            "answer": "Đặt sai thứ tự cột phá vỡ leftmost prefix.",
                        },
                        {
                            "question_id": "q3",
                            "answer": "Tạo composite index (user_id, created_at).",
                        },
                    ],
                    "confidence": 0.8,
                },
            )
            assert sub_resp.status_code == 200, sub_resp.text
            assert sub_resp.json()["is_verified"] is True

            # 3. Weekly Review generation -> consumes 1 credit
            today = date.today()
            wr_payload = {
                "roadmap_id": str(roadmap_id),
                "period_start": (today - timedelta(days=6)).isoformat(),
                "period_end": today.isoformat(),
                "reflection": {"summary": "Hoàn thành tốt các bài tập thực hành."},
            }
            wr_resp = await client.post(
                "/api/v1/evaluation/weekly-reviews/generate-jobs",
                headers=headers,
                json=wr_payload,
            )
            assert wr_resp.status_code == 202, wr_resp.text

            # 4. Duplicate Weekly Review for same period -> idempotent, NO extra quota charged
            wr_dup_resp = await client.post(
                "/api/v1/evaluation/weekly-reviews/generate-jobs",
                headers=headers,
                json=wr_payload,
            )
            assert wr_dup_resp.status_code == 202, wr_dup_resp.text
            assert wr_dup_resp.json()["id"] == wr_resp.json()["id"]

        assert provider.call_count == 3

        async with async_session_factory() as session:
            quota = (
                await session.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == user_id))
            ).scalar_one()
            assert quota.used_calls == 3
            assert quota.reserved_calls == 0
            assert quota.tokens_consumed > 0

            reservations = list(
                (
                    await session.execute(
                        select(AIQuotaReservationORM).where(
                            AIQuotaReservationORM.user_id == user_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(reservations) == 3
            assert all(r.status == "COMMITTED" for r in reservations)

            usage_logs = list(
                (
                    await session.execute(
                        select(AIUsageLogORM).where(AIUsageLogORM.user_id == user_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(usage_logs) == 3
            action_types = sorted(log.action_type for log in usage_logs)
            assert action_types == [
                "AI_REVIEW_MILESTONE",
                "AI_REVIEW_MILESTONE",
                "AI_REVIEW_WEEKLY",
            ]
            assert all(log.status == "SUCCESS" for log in usage_logs)
    finally:
        app.dependency_overrides.pop(get_evaluation_llm_provider, None)
        await _cleanup_eval_user(user_id)


@pytest.mark.asyncio
async def test_premium_tier_quota_enforcement() -> None:
    user_id, _, milestone_id = await _seed_eval_user(
        tier="PREMIUM",
        monthly_limit=300,
        used_calls=299,
    )
    provider = _TrackingEvalLLMProvider()
    app.dependency_overrides[get_evaluation_llm_provider] = lambda: provider
    try:
        headers = _auth_headers(user_id, tier="PREMIUM")
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 300th call succeeds
            ok_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/generate-jobs",
                headers=headers,
            )
            assert ok_resp.status_code == 202, ok_resp.text
            proof_id = ok_resp.json()["proof_id"]
            assert provider.call_count == 1

            # 301st call (Prove submit) is blocked with 429 and LLM is NOT invoked
            blocked_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit",
                headers=headers,
                json={
                    "answers": [{"question_id": "q1", "answer": "Test answer"}],
                    "confidence": 0.7,
                },
            )
            assert blocked_resp.status_code == 429, blocked_resp.text
            assert blocked_resp.json()["code"] == "QUOTA_EXHAUSTED"
            assert provider.call_count == 1
    finally:
        app.dependency_overrides.pop(get_evaluation_llm_provider, None)
        await _cleanup_eval_user(user_id)


@pytest.mark.asyncio
async def test_llm_timeout_releases_quota_reservation_without_charging() -> None:
    user_id, _, milestone_id = await _seed_eval_user(
        tier="FREE",
        monthly_limit=5,
        used_calls=0,
    )
    provider = _TrackingEvalLLMProvider(fail_always=TimeoutError("Simulated LLM timeout"))
    app.dependency_overrides[get_evaluation_llm_provider] = lambda: provider
    try:
        headers = _auth_headers(user_id)
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/generate-jobs",
                headers=headers,
            )
            # GenerateMilestoneProofUseCase falls back gracefully on timeout
            assert resp.status_code == 202, resp.text

        async with async_session_factory() as session:
            quota = (
                await session.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == user_id))
            ).scalar_one()
            assert quota.used_calls == 0
            assert quota.reserved_calls == 0

            reservations = list(
                (
                    await session.execute(
                        select(AIQuotaReservationORM).where(
                            AIQuotaReservationORM.user_id == user_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(reservations) == 1
            assert reservations[0].status == "RELEASED"
    finally:
        app.dependency_overrides.pop(get_evaluation_llm_provider, None)
        await _cleanup_eval_user(user_id)


@pytest.mark.asyncio
async def test_transient_retry_does_not_double_charge_and_concurrent_requests_respect_limit() -> (
    None
):
    # Part 1: Transient failure on attempt 1 + success on attempt 2 -> only 1 credit charged
    retry_user_id, _, retry_ms_id = await _seed_eval_user(
        tier="FREE",
        monthly_limit=5,
        used_calls=0,
    )
    retry_provider = _TrackingEvalLLMProvider(
        fail_first_n=1,
        transient_error=TimeoutError("Transient timeout on attempt 1"),
    )
    app.dependency_overrides[get_evaluation_llm_provider] = lambda: retry_provider
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/evaluation/milestones/{retry_ms_id}/proofs/generate-jobs",
                headers=_auth_headers(retry_user_id),
            )
            assert resp.status_code == 202, resp.text
        assert retry_provider.call_count == 2

        async with async_session_factory() as session:
            quota = (
                await session.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == retry_user_id))
            ).scalar_one()
            assert quota.used_calls == 1
            assert quota.reserved_calls == 0
    finally:
        app.dependency_overrides.pop(get_evaluation_llm_provider, None)
        await _cleanup_eval_user(retry_user_id)

    # Part 2: Concurrent requests when only 1 credit remains -> exactly 1 succeeds, 1 gets 429
    conc_user_id, _, conc_ms_id = await _seed_eval_user(
        tier="FREE",
        monthly_limit=1,
        used_calls=0,
    )
    conc_provider = _TrackingEvalLLMProvider(delay_seconds=0.15)
    app.dependency_overrides[get_evaluation_llm_provider] = lambda: conc_provider
    try:
        headers = _auth_headers(conc_user_id)
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r1, r2 = await asyncio.gather(
                client.post(
                    f"/api/v1/evaluation/milestones/{conc_ms_id}/proofs/generate-jobs",
                    headers=headers,
                ),
                client.post(
                    f"/api/v1/evaluation/milestones/{conc_ms_id}/proofs/generate-jobs",
                    headers=headers,
                ),
            )
        statuses = sorted([r1.status_code, r2.status_code])
        assert statuses == [202, 429], (r1.text, r2.text)
        assert conc_provider.call_count == 1

        async with async_session_factory() as session:
            quota = (
                await session.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == conc_user_id))
            ).scalar_one()
            assert quota.used_calls == 1
            assert quota.reserved_calls == 0
    finally:
        app.dependency_overrides.pop(get_evaluation_llm_provider, None)
        await _cleanup_eval_user(conc_user_id)
