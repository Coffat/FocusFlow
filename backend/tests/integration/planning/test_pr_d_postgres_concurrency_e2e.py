from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text
from uuid6 import uuid7

from src.account.infrastructure.orm.availability_orm import (
    AvailabilityORM,
    AvailabilitySlotORM,
)
from src.account.infrastructure.orm.user_orm import AIQuotaORM, LearnerProfileORM, UserORM
from src.account.presentation.deps import get_current_learner_id
from src.evaluation.infrastructure.orm.schedule_change_log_orm import ScheduleChangeLogORM
from src.execution.infrastructure.orm.task_orm import TaskORM
from src.main import app
from src.planning.infrastructure.orm.planning_orm import (
    OfficialScheduleORM,
    ScheduleBlockORM,
    ScheduleProposalORM,
)
from src.planning.presentation.deps import get_llm_provider
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM
from src.shared_kernel.infrastructure.sse import default_in_memory_sse_job_store
from tests.helpers.llm_stubs import StubLLMAdapter


@pytest.fixture
async def pr_d_user() -> AsyncGenerator[UUID, None]:
    user_id = uuid7()
    now = datetime.now(UTC)
    default_in_memory_sse_job_store.clear()

    async with async_session_factory() as session:
        user = UserORM(
            id=user_id,
            email=f"prd_concurrency_{user_id.hex}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="PR-D Concurrency Learner",
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="PREMIUM",  # Allows multiple ACTIVE roadmaps (OS-02 = 3) to test slot race
            is_locked=False,
        )
        quota = AIQuotaORM(
            id=uuid7(),
            user_id=user_id,
            free_credits_remaining=10,
            paid_credits_remaining=10,
            used_calls=0,
            reserved_calls=0,
            tokens_consumed=0,
            cycle_start=now,
            cycle_end=now + timedelta(days=30),
        )
        profile = LearnerProfileORM(
            id=uuid7(),
            user_id=user_id,
            opt_session_minutes=60,
            estimation_bias_beta=1.0,
            is_cold_start=False,
        )
        avail_id = uuid7()
        avail = AvailabilityORM(
            id=avail_id,
            user_id=user_id,
            mode="MODE_B",
            calendar_integration_mode="NONE",
            min_session_minutes=30,
            daily_quotas={
                "monday": {"enabled": True, "quota_hours": 2.0},
                "tuesday": {"enabled": True, "quota_hours": 2.0},
                "wednesday": {"enabled": True, "quota_hours": 2.0},
            },
        )
        slots = [
            AvailabilitySlotORM(
                id=uuid7(),
                availability_id=avail_id,
                day_of_week=dow,
                slot_type="FIXED",
                start_time=time(19, 0),
                end_time=time(21, 0),
                end_day_offset=0,
                is_active=True,
            )
            for dow in (0, 1, 2)  # Mon, Tue, Wed
        ]
        session.add(user)
        await session.flush()
        session.add_all([quota, profile, avail])
        await session.flush()
        session.add_all(slots)
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
            await session.execute(
                text(
                    "DELETE FROM session_tasks WHERE session_id IN "
                    "(SELECT id FROM study_sessions WHERE user_id = :uid)"
                ),
                {"uid": user_id},
            )
            await session.execute(
                delete(OutboxEventORM).where(OutboxEventORM.aggregate_id == user_id)
            )
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()


async def _create_roadmap_with_manual_proposal(
    client: AsyncClient,
    *,
    title: str,
    task_date: date,
    start_hhmm: str = "19:00",
    end_hhmm: str = "20:00",
    minutes: int = 60,
) -> tuple[UUID, UUID, UUID]:
    rm_res = await client.post(
        "/api/v1/roadmaps",
        json={
            "title": title,
            "description": f"Concurrency test {title}",
            "start_date": task_date.isoformat(),
            "target_date": (task_date + timedelta(days=14)).isoformat(),
        },
    )
    assert rm_res.status_code == 201, rm_res.text
    roadmap_id = UUID(rm_res.json()["id"])

    ms_id = str(uuid7())
    t_id = str(uuid7())
    manual_res = await client.post(
        f"/api/v1/roadmaps/{roadmap_id}/proposals/manual",
        json={
            "milestones": [
                {
                    "milestone_id": ms_id,
                    "sequence_order": 1,
                    "title": f"{title} M1",
                    "description": "M1",
                }
            ],
            "tasks": [
                {
                    "task_id": t_id,
                    "milestone_id": ms_id,
                    "title": f"{title} Task",
                    "estimated_minutes": minutes,
                    "scheduled_date": task_date.isoformat(),
                    "scheduled_start": f"{task_date.isoformat()}T{start_hhmm}:00+07:00",
                    "scheduled_end": f"{task_date.isoformat()}T{end_hhmm}:00+07:00",
                }
            ],
            "dependencies": [],
        },
    )
    assert manual_res.status_code == 201, manual_res.text
    proposal_id = UUID(manual_res.json()["id"])
    return roadmap_id, proposal_id, UUID(t_id)


@pytest.mark.asyncio
async def test_pr_d_double_apply_idempotency_and_non_draft_guards_postgres(
    pr_d_user: UUID,
) -> None:
    """DEF-11: Concurrent double-apply with Idempotency-Key & non-DRAFT guards in real Postgres."""
    del pr_d_user
    transport = ASGITransport(app=app)
    mon = date(2026, 11, 16)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        roadmap_id, proposal_id, _ = await _create_roadmap_with_manual_proposal(
            client,
            title="Double Apply Roadmap",
            task_date=mon,
        )

        # Create a stale/discarded proposal first? No, create P1 then create P2 which discards P1!
        p1_id = proposal_id
        t2_id = str(uuid7())
        ms2_id = str(uuid7())
        p2_res = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/manual",
            json={
                "milestones": [
                    {
                        "milestone_id": ms2_id,
                        "sequence_order": 1,
                        "title": "M1 v2",
                        "description": "M1 v2",
                    }
                ],
                "tasks": [
                    {
                        "task_id": t2_id,
                        "milestone_id": ms2_id,
                        "title": "Task v2",
                        "estimated_minutes": 60,
                        "scheduled_date": mon.isoformat(),
                        "scheduled_start": f"{mon.isoformat()}T19:00:00+07:00",
                        "scheduled_end": f"{mon.isoformat()}T20:00:00+07:00",
                    }
                ],
                "dependencies": [],
            },
        )
        assert p2_res.status_code == 201
        p2_id = UUID(p2_res.json()["id"])

        # Applying discarded P1 must fail cleanly
        stale_apply = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{p1_id}/apply",
            json={"confirm_soft_overflow": False},
        )
        assert stale_apply.status_code == 422
        assert stale_apply.json()["code"] == "INVALID_PROPOSAL_STATE_TRANSITION"

        # Editing discarded P1 must also fail cleanly
        stale_edit = await client.put(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{p1_id}",
            json={
                "tasks": [
                    {
                        "task_id": t2_id,
                        "milestone_id": ms2_id,
                        "title": "Illegal Edit",
                        "estimated_minutes": 60,
                        "scheduled_date": mon.isoformat(),
                        "scheduled_start": f"{mon.isoformat()}T19:00:00+07:00",
                        "scheduled_end": f"{mon.isoformat()}T20:00:00+07:00",
                    }
                ],
                "dependencies": [],
            },
        )
        assert stale_edit.status_code == 422
        assert stale_edit.json()["code"] == "INVALID_PROPOSAL_STATE_TRANSITION"

        # Concurrent double-apply on P2 with same Idempotency-Key
        r_a, r_b = await asyncio.gather(
            client.post(
                f"/api/v1/roadmaps/{roadmap_id}/proposals/{p2_id}/apply",
                json={"confirm_soft_overflow": False},
                headers={"Idempotency-Key": "pr-d-double-apply-1"},
            ),
            client.post(
                f"/api/v1/roadmaps/{roadmap_id}/proposals/{p2_id}/apply",
                json={"confirm_soft_overflow": False},
                headers={"Idempotency-Key": "pr-d-double-apply-1"},
            ),
        )
        assert r_a.status_code == 200, r_a.text
        assert r_b.status_code == 200, r_b.text
        assert r_a.json()["official_schedule_id"] == r_b.json()["official_schedule_id"]

        # Editing APPLIED P2 must also be rejected
        edit_applied = await client.put(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{p2_id}",
            json={
                "tasks": [
                    {
                        "task_id": t2_id,
                        "milestone_id": ms2_id,
                        "title": "Illegal Edit After Apply",
                        "estimated_minutes": 60,
                        "scheduled_date": mon.isoformat(),
                        "scheduled_start": f"{mon.isoformat()}T19:00:00+07:00",
                        "scheduled_end": f"{mon.isoformat()}T20:00:00+07:00",
                    }
                ],
                "dependencies": [],
            },
        )
        assert edit_applied.status_code == 422
        assert edit_applied.json()["code"] == "INVALID_PROPOSAL_STATE_TRANSITION"

    # Verify PostgreSQL contains exactly 1 schedule, 1 task, 1 planned block, 1 change log
    async with async_session_factory() as session:
        schedules = list(
            (
                await session.execute(
                    select(OfficialScheduleORM).where(OfficialScheduleORM.roadmap_id == roadmap_id)
                )
            )
            .scalars()
            .all()
        )
        tasks = list(
            (await session.execute(select(TaskORM).where(TaskORM.roadmap_id == roadmap_id)))
            .scalars()
            .all()
        )
        blocks = list(
            (
                await session.execute(
                    select(ScheduleBlockORM).where(
                        ScheduleBlockORM.roadmap_id == roadmap_id,
                        ScheduleBlockORM.status == "PLANNED",
                    )
                )
            )
            .scalars()
            .all()
        )
        logs = list(
            (
                await session.execute(
                    select(ScheduleChangeLogORM).where(
                        ScheduleChangeLogORM.roadmap_id == roadmap_id
                    )
                )
            )
            .scalars()
            .all()
        )
        prop_p2 = await session.get(ScheduleProposalORM, p2_id)
        assert len(schedules) == 1
        assert len(tasks) == 1
        assert len(blocks) == 1
        assert len(logs) == 1
        assert prop_p2 is not None and prop_p2.status == "APPLIED"


@pytest.mark.asyncio
async def test_pr_d_two_roadmaps_concurrent_apply_overlapping_slots_zero_double_booking(
    pr_d_user: UUID,
) -> None:
    """DEF-11: Two roadmaps of the same user racing concurrently to Apply overlapping slots -> 1 succeeds, 1 rejected."""
    del pr_d_user
    transport = ASGITransport(app=app)
    mon = date(2026, 11, 16)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1_id, p1_id, _ = await _create_roadmap_with_manual_proposal(
            client,
            title="Concurrent Roadmap 1",
            task_date=mon,
            start_hhmm="19:00",
            end_hhmm="20:00",
        )
        r2_id, p2_id, _ = await _create_roadmap_with_manual_proposal(
            client,
            title="Concurrent Roadmap 2",
            task_date=mon,
            start_hhmm="19:00",
            end_hhmm="20:00",
        )

        res1, res2 = await asyncio.gather(
            client.post(
                f"/api/v1/roadmaps/{r1_id}/proposals/{p1_id}/apply",
                json={"confirm_soft_overflow": False},
            ),
            client.post(
                f"/api/v1/roadmaps/{r2_id}/proposals/{p2_id}/apply",
                json={"confirm_soft_overflow": False},
            ),
        )

        statuses = sorted([res1.status_code, res2.status_code])
        assert statuses[0] == 200, (
            f"Expected one 200 and one 409/422, got {[res1.status_code, res2.status_code]}: {res1.text} / {res2.text}"
        )
        assert statuses[1] in (409, 422), (
            f"Expected second concurrent overlapping Apply to fail with 409/422, got {statuses}: "
            f"{res1.text} / {res2.text}"
        )

    async with async_session_factory() as session:
        planned_blocks = list(
            (
                await session.execute(
                    select(ScheduleBlockORM).where(
                        ScheduleBlockORM.roadmap_id.in_([r1_id, r2_id]),
                        ScheduleBlockORM.status == "PLANNED",
                    )
                )
            )
            .scalars()
            .all()
        )
        tasks = list(
            (await session.execute(select(TaskORM).where(TaskORM.roadmap_id.in_([r1_id, r2_id]))))
            .scalars()
            .all()
        )
        assert len(planned_blocks) == 1, f"Double-booked blocks in DB: {planned_blocks}"
        assert len(tasks) == 1, f"Double-booked tasks in DB: {tasks}"


@pytest.mark.asyncio
async def test_pr_d_resume_roadmap_rejects_cross_roadmap_slot_conflict(
    pr_d_user: UUID,
) -> None:
    """DEF-11: Resuming PAUSED R2 with Domino shift landing onto ACTIVE R1's occupied slot must be rejected."""
    del pr_d_user
    transport = ASGITransport(app=app)
    mon = date(2026, 11, 16)
    tue = date(2026, 11, 17)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # R1 occupies Tuesday 19:00-20:00
        r1_id, p1_id, _ = await _create_roadmap_with_manual_proposal(
            client,
            title="Active R1 on Tue",
            task_date=tue,
            start_hhmm="19:00",
            end_hhmm="20:00",
        )
        app1 = await client.post(
            f"/api/v1/roadmaps/{r1_id}/proposals/{p1_id}/apply",
            json={"confirm_soft_overflow": False},
        )
        assert app1.status_code == 200, app1.text

        # R2 occupies Monday 19:00-20:00, then gets PAUSED
        r2_id, p2_id, _ = await _create_roadmap_with_manual_proposal(
            client,
            title="Paused R2 on Mon",
            task_date=mon,
            start_hhmm="19:00",
            end_hhmm="20:00",
        )
        app2 = await client.post(
            f"/api/v1/roadmaps/{r2_id}/proposals/{p2_id}/apply",
            json={"confirm_soft_overflow": False},
        )
        assert app2.status_code == 200, app2.text

        pause_res = await client.post(f"/api/v1/roadmaps/{r2_id}/pause")
        assert pause_res.status_code == 200, pause_res.text

        # Resume R2 with shift_days=1 -> Monday 19:00-20:00 shifts onto Tuesday 19:00-20:00 (collides with R1!)
        resume_res = await client.post(f"/api/v1/roadmaps/{r2_id}/resume?shift_days=1")
        assert resume_res.status_code in (409, 422), (
            f"Expected resume conflict 409/422, got {resume_res.status_code}: {resume_res.text}"
        )
