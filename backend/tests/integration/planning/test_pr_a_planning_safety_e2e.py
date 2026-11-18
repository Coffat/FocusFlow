from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, time, timedelta
from typing import Any
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from uuid6 import uuid7

from src.account.infrastructure.orm.availability_orm import (
    AvailabilityORM,
    AvailabilitySlotORM,
)
from src.account.infrastructure.orm.user_orm import (
    AIQuotaORM,
    AIQuotaReservationORM,
    UserORM,
)
from src.account.presentation.deps import get_current_learner_id
from src.main import app
from src.planning.infrastructure.orm.planning_orm import ScheduleProposalORM
from src.planning.presentation.deps import get_llm_provider
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.sse import default_in_memory_sse_job_store
from tests.helpers.llm_stubs import StubLLMAdapter


@pytest.fixture
async def pr_a_user() -> AsyncGenerator[UUID, None]:
    user_id = uuid7()
    now = datetime.now(UTC)
    default_in_memory_sse_job_store.clear()

    async with async_session_factory() as session:
        user = UserORM(
            id=user_id,
            email=f"pra_owner_{user_id.hex}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="PR-A Test Learner",
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE",
            is_locked=False,
        )
        quota = AIQuotaORM(
            id=uuid7(),
            user_id=user_id,
            free_credits_remaining=10,
            paid_credits_remaining=0,
            used_calls=0,
            reserved_calls=0,
            tokens_consumed=0,
            cycle_start=now,
            cycle_end=now + timedelta(days=30),
        )
        session.add(user)
        await session.flush()
        session.add(quota)
        await session.commit()

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_learner_id] = lambda: user_id
    app.dependency_overrides[get_llm_provider] = lambda: StubLLMAdapter()

    try:
        yield user_id
    finally:
        app.dependency_overrides.clear()
        default_in_memory_sse_job_store.clear()
        async with async_session_factory() as session:
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()


def _parse_sse_completed_payload(sse_text: str) -> dict[str, Any]:
    for block in sse_text.split("\n\n"):
        if "event: completed" in block:
            for line in block.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[len("data:") :].strip())  # type: ignore[no-any-return]
    return {}


@pytest.mark.asyncio
async def test_e2e_pr_a_generate_validate_and_apply_safety_workflow(pr_a_user: UUID) -> None:
    user_id = pr_a_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create roadmap & approve milestones
        create_res = await client.post(
            "/api/v1/roadmaps",
            json={
                "title": "PR-A Safety E2E Roadmap",
                "description": "Kiểm thử validation gate và apply safety",
                "start_date": "2026-11-16",
                "target_date": "2026-11-22",
            },
        )
        assert create_res.status_code == 201
        roadmap_id = UUID(create_res.json()["id"])

        ms_job = await client.post(f"/api/v1/roadmaps/{roadmap_id}/milestones/generate-jobs")
        assert ms_job.status_code == 202
        await client.get(ms_job.json()["stream_url"])

        detail = (await client.get(f"/api/v1/roadmaps/{roadmap_id}")).json()
        ms_list = detail["milestones"]
        await client.put(
            f"/api/v1/roadmaps/{roadmap_id}/milestones",
            json={
                "milestones": [
                    {
                        "id": ms_list[0]["id"],
                        "sequence_order": 1,
                        "title": ms_list[0]["title"],
                        "description": ms_list[0].get("description") or "",
                        "estimated_effort_minutes": 120,
                    }
                ]
            },
        )
        approve_res = await client.post(f"/api/v1/roadmaps/{roadmap_id}/milestones/approve")
        assert approve_res.status_code == 200, approve_res.text
        m1_id = approve_res.json()["milestones"][0]["id"]

        # 2. Zero availability -> caught synchronously with 409 PRELIMINARY_UNSCHEDULABLE (0 quota reserved),
        #    and 60m slot with non-splittable 120m tasks -> generation MUST fail-closed in SSE (PLAN_INFEASIBLE, quota RELEASED)
        async with async_session_factory() as session:
            avail_zero = AvailabilityORM(
                id=uuid7(),
                user_id=user_id,
                mode="MODE_B",
                calendar_integration_mode="NONE",
                min_session_minutes=30,
                daily_quotas={
                    day: {"enabled": False, "quota_hours": 0.0}
                    for day in (
                        "monday",
                        "tuesday",
                        "wednesday",
                        "thursday",
                        "friday",
                        "saturday",
                        "sunday",
                    )
                },
            )
            session.add(avail_zero)
            await session.commit()

        zero_blocked = await client.post(f"/api/v1/roadmaps/{roadmap_id}/proposals/generate-jobs")
        assert zero_blocked.status_code == 409
        assert zero_blocked.json()["code"] == "PRELIMINARY_UNSCHEDULABLE"

        # Restore 90m Monday slot (passes preliminary feasibility for 120m milestone since E_min=90),
        # then feed non-splittable 120m task so Stage 2 Task Decomposer fails closed with PLAN_INFEASIBLE
        async with async_session_factory() as session:
            await session.execute(delete(AvailabilityORM).where(AvailabilityORM.user_id == user_id))
            avail_90_id = uuid7()
            avail_90 = AvailabilityORM(
                id=avail_90_id,
                user_id=user_id,
                mode="MODE_B",
                calendar_integration_mode="NONE",
                min_session_minutes=30,
                daily_quotas={"monday": {"enabled": True, "quota_hours": 1.5}},
            )
            slot_90 = AvailabilitySlotORM(
                id=uuid7(),
                availability_id=avail_90_id,
                day_of_week=0,
                slot_type="FIXED",
                start_time=time(19, 0),
                end_time=time(20, 30),
                end_day_offset=0,
                is_active=True,
            )
            session.add(avail_90)
            await session.flush()
            session.add(slot_90)
            await session.commit()
        # Re-approve milestone after zero-capacity invalidation
        reapprove_res = await client.post(f"/api/v1/roadmaps/{roadmap_id}/milestones/approve")
        assert reapprove_res.status_code == 200, reapprove_res.text

        t1_id = str(uuid7())
        t2_id = str(uuid7())
        canned_infeasible = {
            "tasks": [
                {
                    "task_id": t1_id,
                    "milestone_id": m1_id,
                    "title": "Bài kiểm thử thực hành toàn diện 120 phút",
                    "learning_objective": "Vượt qua bài kiểm thử tổng hợp.",
                    "completion_criteria": "Đạt điểm tối đa.",
                    "covered_outcome_ids": [
                        f"M1-O{i}"
                        for i in range(1, len(ms_list[0].get("learning_outcomes", [])) + 1)
                    ]
                    or ["M1-O1", "M1-O2"],
                    "concept_ids": list(ms_list[0].get("required_concepts") or []),
                    "estimated_minutes": 120,
                    "is_non_splittable": True,
                }
            ],
            "dependencies": [],
        }
        canned_partial = {
            "tasks": [
                {
                    "task_id": t1_id,
                    "milestone_id": m1_id,
                    "title": "Bài 1: Nền tảng",
                    "learning_objective": "Nắm nền tảng.",
                    "completion_criteria": "Pass quiz.",
                    "covered_outcome_ids": ["M1-O1"],
                    "concept_ids": [],
                    "estimated_minutes": 60,
                },
                {
                    "task_id": t2_id,
                    "milestone_id": m1_id,
                    "title": "Bài 2: Thực hành",
                    "learning_objective": "Thực hành bài tập.",
                    "completion_criteria": "Pass test.",
                    "covered_outcome_ids": [],
                    "concept_ids": [],
                    "estimated_minutes": 60,
                },
            ],
            "dependencies": [
                {"predecessor_id": t1_id, "successor_id": t2_id, "is_mandatory": True}
            ],
        }
        app.dependency_overrides[get_llm_provider] = lambda: StubLLMAdapter(
            canned_responses=[canned_infeasible, canned_infeasible, canned_infeasible]
        )

        zero_job = await client.post(f"/api/v1/roadmaps/{roadmap_id}/proposals/generate-jobs")
        assert zero_job.status_code == 202
        zero_sse = await client.get(zero_job.json()["stream_url"])
        assert "event: failed" in zero_sse.text
        assert "PLAN_INFEASIBLE" in zero_sse.text

        async with async_session_factory() as session:
            drafts = list(
                (
                    await session.execute(
                        select(ScheduleProposalORM).where(
                            ScheduleProposalORM.roadmap_id == roadmap_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(drafts) == 0
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
            assert any(r.status == "RELEASED" for r in reservations)

        # 3. With Monday 90m slot -> 1 of 2 (60m) tasks scheduled (50% >= 25%) -> PARTIAL schedule
        #    (existing avail_90 from step 2 already has Monday 90m slot)

        app.dependency_overrides[get_llm_provider] = lambda: StubLLMAdapter(
            canned_responses=[canned_partial, canned_partial]
        )
        partial_job = await client.post(f"/api/v1/roadmaps/{roadmap_id}/proposals/generate-jobs")
        assert partial_job.status_code == 202
        partial_sse = await client.get(partial_job.json()["stream_url"])
        assert "event: completed" in partial_sse.text
        completed_data = _parse_sse_completed_payload(partial_sse.text)
        payload = completed_data["payload"]
        assert payload["schedule_completeness_status"] == "PARTIAL"
        assert "feasibility" in payload
        assert "feasibility_verdict" in payload

        curr = await client.get(f"/api/v1/roadmaps/{roadmap_id}/proposals/current")
        assert curr.status_code == 200
        curr_json = curr.json()
        assert curr_json["schedule_completeness_status"] == "PARTIAL"
        proposal_id = curr_json["id"]

        # 4. Apply PARTIAL without confirm_partial_schedule -> 409 PARTIAL_SCHEDULE_CONFIRMATION_REQUIRED
        apply_no_confirm = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{proposal_id}/apply",
            json={"confirm_partial_schedule": False},
        )
        assert apply_no_confirm.status_code == 409
        assert apply_no_confirm.json()["code"] == "PARTIAL_SCHEDULE_CONFIRMATION_REQUIRED"

        # 5. Apply PARTIAL with confirm_partial_schedule=True -> 200 OK
        apply_ok = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{proposal_id}/apply",
            json={"confirm_partial_schedule": True, "confirm_warnings": True},
        )
        assert apply_ok.status_code == 200
        assert apply_ok.json()["backlog_unscheduled_tasks_count"] == 1
