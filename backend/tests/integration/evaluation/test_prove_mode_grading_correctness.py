"""Integration tests for Prove Mode AI evaluation correctness (AUD-MED-12)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport
from pydantic import ValidationError
from sqlalchemy import delete, select
from uuid6 import uuid7

from src.account.infrastructure.orm.learner_memory_orm import (
    LearnerConceptMasteryORM,
    LearnerMemoryItemORM,
)
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
)
from src.evaluation.infrastructure.orm.milestone_proof_orm import MilestoneProofORM
from src.evaluation.presentation.deps import get_evaluation_llm_provider
from src.main import app
from src.planning.infrastructure.orm.planning_orm import GoalORM, MilestoneORM, RoadmapORM
from src.shared_kernel.application.llm_port import LLMGenerationResult
from src.shared_kernel.infrastructure.database.session import async_session_factory


class _ConfigurableProveLLMProvider:
    """Deterministic stub provider supporting success, genuine zero, timeout, and invalid payloads."""

    def __init__(
        self,
        *,
        grading_payload: dict[str, Any] | None = None,
        grading_error: Exception | None = None,
    ) -> None:
        self.grading_payload = grading_payload
        self.grading_error = grading_error
        self.generate_calls = 0
        self.grade_calls = 0

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
            self.generate_calls += 1
            payload = ProveQuestionsLLMOutput(
                questions=[
                    ProveQuestionItemSchema(id="q1", prompt="Giải thích cơ chế MVCC."),
                    ProveQuestionItemSchema(
                        id="q2", prompt="Nêu một lỗi thường gặp khi dùng lock."
                    ),
                    ProveQuestionItemSchema(id="q3", prompt="Áp dụng vào giao dịch đặt chỗ."),
                ]
            ).model_dump()
            return LLMGenerationResult(
                payload=payload,
                prompt_tokens=80,
                output_tokens=100,
                model_id="mock-prove-correctness",
            )
        if response_schema is ProveGradingLLMOutput:
            self.grade_calls += 1
            if self.grading_error is not None:
                raise self.grading_error
            assert self.grading_payload is not None
            return LLMGenerationResult(
                payload=self.grading_payload,
                prompt_tokens=120,
                output_tokens=140,
                model_id="mock-prove-correctness",
            )
        raise AssertionError(f"Unexpected schema requested: {response_schema}")


def _make_grade_payload(
    conceptual: int,
    example: int,
    practical: int,
    *,
    corrective_action: str | None = None,
) -> dict[str, Any]:
    return ProveGradingLLMOutput(
        conceptual_understanding_score=conceptual,
        example_grounding_score=example,
        practical_application_score=practical,
        answer_evidence=[
            ProveAnswerFeedbackSchema(
                question_id="q1",
                evidence="Đánh giá câu 1.",
                is_addressed=conceptual > 0,
            ),
            ProveAnswerFeedbackSchema(
                question_id="q2",
                evidence="Đánh giá câu 2.",
                is_addressed=example > 0,
            ),
            ProveAnswerFeedbackSchema(
                question_id="q3",
                evidence="Đánh giá câu 3.",
                is_addressed=practical > 0,
            ),
        ],
        corrective_action=corrective_action,
    ).model_dump()


async def _seed_user_milestone_and_proof(
    *,
    monthly_limit: int = 10,
    used_calls: int = 0,
    create_ready_proof: bool = True,
) -> tuple[UUID, UUID, UUID, UUID | None]:
    owner_id = uuid7()
    other_user_id = uuid7()
    goal_id = uuid7()
    roadmap_id = uuid7()
    milestone_id = uuid7()
    proof_id: UUID | None = uuid7() if create_ready_proof else None
    now = datetime.now(UTC)

    async with async_session_factory() as session:
        session.add_all(
            [
                UserORM(
                    id=owner_id,
                    email=f"prove_corr_owner_{owner_id.hex}@focusflow.vn",
                    password_hash="argon2id$mockhash",
                    full_name="Prove Correctness Owner",
                    timezone="Asia/Ho_Chi_Minh",
                    role="LEARNER",
                    tier="FREE",
                    is_locked=False,
                ),
                UserORM(
                    id=other_user_id,
                    email=f"prove_corr_other_{other_user_id.hex}@focusflow.vn",
                    password_hash="argon2id$mockhash",
                    full_name="Prove Correctness Other",
                    timezone="Asia/Ho_Chi_Minh",
                    role="LEARNER",
                    tier="FREE",
                    is_locked=False,
                ),
            ]
        )
        await session.flush()

        session.add(
            AIQuotaORM(
                id=uuid7(),
                user_id=owner_id,
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
                user_id=owner_id,
                title="PostgreSQL Concurrency",
                raw_description="Master MVCC and transaction isolation",
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
                title="PostgreSQL Concurrency Roadmap",
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
                title="MVCC & Isolation Levels",
                description="Understand snapshot isolation and locks",
                learning_outcomes=["Explain MVCC", "Prevent write skew"],
                status="IN_PROGRESS",
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()

        if proof_id is not None:
            session.add(
                MilestoneProofORM(
                    id=proof_id,
                    milestone_id=milestone_id,
                    user_id=owner_id,
                    status="READY",
                    questions=[
                        {"id": "q1", "prompt": "Giải thích cơ chế MVCC."},
                        {"id": "q2", "prompt": "Nêu một lỗi thường gặp khi dùng lock."},
                        {"id": "q3", "prompt": "Áp dụng vào giao dịch đặt chỗ."},
                    ],
                    created_at=now,
                )
            )
        await session.commit()

    return owner_id, other_user_id, milestone_id, proof_id


async def _cleanup_users(*user_ids: UUID) -> None:
    id_list = list(user_ids)
    async with async_session_factory() as session:
        await session.execute(delete(AIUsageLogORM).where(AIUsageLogORM.user_id.in_(id_list)))
        await session.execute(
            delete(AIQuotaReservationORM).where(AIQuotaReservationORM.user_id.in_(id_list))
        )
        await session.execute(delete(AIQuotaORM).where(AIQuotaORM.user_id.in_(id_list)))
        await session.execute(
            delete(LearnerConceptMasteryORM).where(LearnerConceptMasteryORM.user_id.in_(id_list))
        )
        await session.execute(
            delete(LearnerMemoryItemORM).where(LearnerMemoryItemORM.user_id.in_(id_list))
        )
        await session.execute(delete(UserORM).where(UserORM.id.in_(id_list)))
        await session.commit()


def _auth_headers(user_id: UUID) -> dict[str, str]:
    token = JwtTokenProvider.create_access_token(
        user_id=user_id,
        email=f"prove_corr_{user_id.hex}@focusflow.vn",
        role="LEARNER",
        tier="FREE",
    )
    return {"Authorization": f"Bearer {token}"}


_SAMPLE_ANSWERS = {
    "answers": [
        {"question_id": "q1", "answer": "MVCC giữ nhiều phiên bản hàng để đọc không chặn ghi."},
        {"question_id": "q2", "answer": "Giữ lock quá lâu gây deadlock hoặc contention."},
        {"question_id": "q3", "answer": "Dùng SELECT FOR UPDATE trên dòng quota."},
    ],
    "confidence": 0.75,
}


@pytest.mark.asyncio
async def test_valid_grading_passed_and_needs_review_persisted_and_restored() -> None:
    owner_id, other_user_id, milestone_id, proof_pass_id = await _seed_user_milestone_and_proof()
    assert proof_pass_id is not None
    provider = _ConfigurableProveLLMProvider(
        grading_payload=_make_grade_payload(32, 24, 24)  # 80 -> PASSED
    )
    app.dependency_overrides[get_evaluation_llm_provider] = lambda: provider
    try:
        headers = _auth_headers(owner_id)
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. PASSED (>= 70)
            pass_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_pass_id}/submit",
                headers=headers,
                json=_SAMPLE_ANSWERS,
            )
            assert pass_resp.status_code == 200, pass_resp.text
            pass_data = pass_resp.json()
            assert pass_data["status"] == "PASSED"
            assert pass_data["score"] == 80
            assert pass_data["is_verified"] is True

            latest_pass = await client.get(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/latest",
                headers=headers,
            )
            assert latest_pass.status_code == 200
            latest_pass_data = latest_pass.json()
            assert latest_pass_data["status"] == "PASSED"
            assert latest_pass_data["score"] == 80
            assert latest_pass_data["is_verified"] is True

            # 2. NEEDS_REVIEW (< 70) on a newly generated proof
            gen_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/generate-jobs",
                headers=headers,
            )
            assert gen_resp.status_code == 202, gen_resp.text
            proof_review_id = gen_resp.json()["proof_id"]

            provider.grading_payload = _make_grade_payload(
                20, 15, 10, corrective_action="Ôn lại phần viết ví dụ cụ thể."
            )  # 45 -> NEEDS_REVIEW
            review_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_review_id}/submit",
                headers=headers,
                json=_SAMPLE_ANSWERS,
            )
            assert review_resp.status_code == 200, review_resp.text
            review_data = review_resp.json()
            assert review_data["status"] == "NEEDS_REVIEW"
            assert review_data["score"] == 45
            assert review_data["is_verified"] is True
            assert review_data["corrective_action"] == "Ôn lại phần viết ví dụ cụ thể."

            latest_review = await client.get(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/latest",
                headers=headers,
            )
            assert latest_review.status_code == 200
            latest_review_data = latest_review.json()
            assert latest_review_data["id"] == proof_review_id
            assert latest_review_data["status"] == "NEEDS_REVIEW"
            assert latest_review_data["score"] == 45
            assert latest_review_data["is_verified"] is True
    finally:
        app.dependency_overrides.pop(get_evaluation_llm_provider, None)
        await _cleanup_users(owner_id, other_user_id)


@pytest.mark.asyncio
async def test_genuine_zero_score_persists_as_verified_and_restores_accurately() -> None:
    owner_id, other_user_id, milestone_id, proof_id = await _seed_user_milestone_and_proof()
    assert proof_id is not None
    provider = _ConfigurableProveLLMProvider(
        grading_payload=_make_grade_payload(
            0, 0, 0, corrective_action="Câu trả lời chưa đúng nội dung, cần học lại từ đầu."
        )
    )
    app.dependency_overrides[get_evaluation_llm_provider] = lambda: provider
    try:
        headers = _auth_headers(owner_id)
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            submit_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit",
                headers=headers,
                json={
                    "answers": [{"question_id": "q1", "answer": "không liên quan"}],
                    "confidence": 0.6,
                },
            )
            assert submit_resp.status_code == 200, submit_resp.text
            data = submit_resp.json()
            assert data["status"] == "NEEDS_REVIEW"
            assert data["score"] == 0
            assert data["is_verified"] is True
            assert data["calibration_error"] == pytest.approx(0.6, abs=1e-4)

            # Reload via GET /proofs/latest -> must restore verified score=0 (NOT unverified!)
            latest_resp = await client.get(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/latest",
                headers=headers,
            )
            assert latest_resp.status_code == 200, latest_resp.text
            latest = latest_resp.json()
            assert latest["id"] == str(proof_id)
            assert latest["status"] == "NEEDS_REVIEW"
            assert latest["score"] == 0
            assert latest["is_verified"] is True
            assert latest["calibration_error"] == pytest.approx(0.6, abs=1e-4)

            # Duplicate submission on genuine score=0 proof -> 409 Conflict, NOT overwritten!
            dup_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit",
                headers=headers,
                json=_SAMPLE_ANSWERS,
            )
            assert dup_resp.status_code == 409, dup_resp.text
            assert dup_resp.json()["code"] == "PROOF_ALREADY_GRADED"
            assert provider.grade_calls == 1
    finally:
        app.dependency_overrides.pop(get_evaluation_llm_provider, None)
        await _cleanup_users(owner_id, other_user_id)


@pytest.mark.asyncio
async def test_provider_timeout_returns_503_preserves_ready_proof_releases_quota_and_allows_retry() -> (
    None
):
    owner_id, other_user_id, milestone_id, proof_id = await _seed_user_milestone_and_proof(
        monthly_limit=5, used_calls=0
    )
    assert proof_id is not None
    provider = _ConfigurableProveLLMProvider(
        grading_error=TimeoutError("Simulated LLM grader timeout")
    )
    app.dependency_overrides[get_evaluation_llm_provider] = lambda: provider
    try:
        headers = _auth_headers(owner_id)
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. Submit fails with timeout -> 503 AI_GRADING_UNAVAILABLE
            fail_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit",
                headers=headers,
                json=_SAMPLE_ANSWERS,
            )
            assert fail_resp.status_code == 503, fail_resp.text
            fail_body = fail_resp.json()
            assert fail_body["code"] == "AI_GRADING_UNAVAILABLE"
            assert "detail" in fail_body

            # 2. Verify DB proof is untouched (READY, score=None, submitted_at=None) & quota released
            async with async_session_factory() as session:
                db_proof = (
                    await session.execute(
                        select(MilestoneProofORM).where(MilestoneProofORM.id == proof_id)
                    )
                ).scalar_one()
                assert db_proof.status == "READY"
                assert db_proof.score is None
                assert db_proof.submitted_at is None

                quota = (
                    await session.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == owner_id))
                ).scalar_one()
                assert quota.used_calls == 0
                assert quota.reserved_calls == 0

                mastery = (
                    await session.execute(
                        select(LearnerConceptMasteryORM).where(
                            LearnerConceptMasteryORM.user_id == owner_id
                        )
                    )
                ).scalar_one_or_none()
                assert mastery is None

            # GET /proofs/latest still shows ungraded READY proof with is_verified=False
            latest_before_retry = await client.get(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/latest",
                headers=headers,
            )
            assert latest_before_retry.status_code == 200
            assert latest_before_retry.json()["status"] == "READY"
            assert latest_before_retry.json()["score"] is None
            assert latest_before_retry.json()["is_verified"] is False

            # 3. Retry with working provider on the EXACT SAME proof_id -> succeeds & charges quota ONCE
            provider.grading_error = None
            provider.grading_payload = _make_grade_payload(35, 25, 25)  # 85 -> PASSED
            retry_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit",
                headers=headers,
                json=_SAMPLE_ANSWERS,
            )
            assert retry_resp.status_code == 200, retry_resp.text
            retry_data = retry_resp.json()
            assert retry_data["id"] == str(proof_id)
            assert retry_data["status"] == "PASSED"
            assert retry_data["score"] == 85
            assert retry_data["is_verified"] is True

            async with async_session_factory() as session:
                quota = (
                    await session.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == owner_id))
                ).scalar_one()
                assert quota.used_calls == 1
                assert quota.reserved_calls == 0

                mastery = (
                    await session.execute(
                        select(LearnerConceptMasteryORM).where(
                            LearnerConceptMasteryORM.user_id == owner_id,
                            LearnerConceptMasteryORM.concept_key == f"milestone:{milestone_id}",
                        )
                    )
                ).scalar_one_or_none()
                assert mastery is not None
                assert float(mastery.mastery_score) == pytest.approx(0.85, abs=1e-4)
    finally:
        app.dependency_overrides.pop(get_evaluation_llm_provider, None)
        await _cleanup_users(owner_id, other_user_id)


@pytest.mark.asyncio
async def test_invalid_structured_output_returns_503_no_fake_zero_and_no_mastery_update() -> None:
    owner_id, other_user_id, milestone_id, proof_id = await _seed_user_milestone_and_proof()
    assert proof_id is not None

    try:
        ProveGradingLLMOutput.model_validate({"conceptual_understanding_score": "not-a-number"})
        raise AssertionError("Expected ValidationError")
    except ValidationError as validation_err:
        provider = _ConfigurableProveLLMProvider(grading_error=validation_err)

    app.dependency_overrides[get_evaluation_llm_provider] = lambda: provider
    try:
        headers = _auth_headers(owner_id)
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit",
                headers=headers,
                json=_SAMPLE_ANSWERS,
            )
            assert resp.status_code == 503, resp.text
            assert resp.json()["code"] == "AI_GRADING_UNAVAILABLE"

        async with async_session_factory() as session:
            db_proof = (
                await session.execute(
                    select(MilestoneProofORM).where(MilestoneProofORM.id == proof_id)
                )
            ).scalar_one()
            assert db_proof.status == "READY"
            assert db_proof.score is None
            assert db_proof.submitted_at is None

            mastery = (
                await session.execute(
                    select(LearnerConceptMasteryORM).where(
                        LearnerConceptMasteryORM.user_id == owner_id
                    )
                )
            ).scalar_one_or_none()
            assert mastery is None
    finally:
        app.dependency_overrides.pop(get_evaluation_llm_provider, None)
        await _cleanup_users(owner_id, other_user_id)


@pytest.mark.asyncio
async def test_duplicate_submit_on_passed_proof_returns_409_without_llm_or_quota() -> None:
    owner_id, other_user_id, milestone_id, proof_id = await _seed_user_milestone_and_proof(
        monthly_limit=5, used_calls=0
    )
    assert proof_id is not None
    provider = _ConfigurableProveLLMProvider(
        grading_payload=_make_grade_payload(36, 28, 26)  # 90 -> PASSED
    )
    app.dependency_overrides[get_evaluation_llm_provider] = lambda: provider
    try:
        headers = _auth_headers(owner_id)
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit",
                headers=headers,
                json=_SAMPLE_ANSWERS,
            )
            assert first_resp.status_code == 200, first_resp.text
            assert first_resp.json()["score"] == 90
            assert provider.grade_calls == 1

            # Second submit on already-graded proof -> 409 Conflict
            dup_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit",
                headers=headers,
                json=_SAMPLE_ANSWERS,
            )
            assert dup_resp.status_code == 409, dup_resp.text
            assert dup_resp.json()["code"] == "PROOF_ALREADY_GRADED"
            assert provider.grade_calls == 1

        async with async_session_factory() as session:
            db_proof = (
                await session.execute(
                    select(MilestoneProofORM).where(MilestoneProofORM.id == proof_id)
                )
            ).scalar_one()
            assert db_proof.status == "PASSED"
            assert db_proof.score == 90

            quota = (
                await session.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == owner_id))
            ).scalar_one()
            assert quota.used_calls == 1
            assert quota.reserved_calls == 0
    finally:
        app.dependency_overrides.pop(get_evaluation_llm_provider, None)
        await _cleanup_users(owner_id, other_user_id)


@pytest.mark.asyncio
async def test_quota_exhausted_returns_429_and_multi_user_submit_returns_404() -> None:
    owner_id, other_user_id, milestone_id, proof_id = await _seed_user_milestone_and_proof(
        monthly_limit=3, used_calls=3
    )
    assert proof_id is not None
    provider = _ConfigurableProveLLMProvider(grading_payload=_make_grade_payload(30, 20, 20))
    app.dependency_overrides[get_evaluation_llm_provider] = lambda: provider
    try:
        owner_headers = _auth_headers(owner_id)
        other_headers = _auth_headers(other_user_id)
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. Quota exhausted -> 429 QUOTA_EXHAUSTED, LLM not invoked
            quota_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit",
                headers=owner_headers,
                json=_SAMPLE_ANSWERS,
            )
            assert quota_resp.status_code == 429, quota_resp.text
            assert quota_resp.json()["code"] == "QUOTA_EXHAUSTED"
            assert provider.grade_calls == 0

            # 2. Multi-user IDOR: User B gets 404 on User A's proof submit
            idor_resp = await client.post(
                f"/api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit",
                headers=other_headers,
                json=_SAMPLE_ANSWERS,
            )
            assert idor_resp.status_code == 404, idor_resp.text
            assert provider.grade_calls == 0
    finally:
        app.dependency_overrides.pop(get_evaluation_llm_provider, None)
        await _cleanup_users(owner_id, other_user_id)
