from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, timedelta
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
from src.evaluation.infrastructure.orm.schedule_change_log_orm import (
    ScheduleChangeLogORM,
)
from src.execution.infrastructure.orm.task_orm import TaskDependencyORM, TaskORM
from src.main import app
from src.planning.presentation.deps import get_llm_provider
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import MockLLMAdapter
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM
from src.shared_kernel.infrastructure.sse import default_in_memory_sse_job_store


@pytest.fixture
async def planning_users() -> AsyncGenerator[tuple[UUID, UUID], None]:
    """Seed two real learners (owner & other_user) with AI quotas in PostgreSQL 16."""
    owner_id = uuid7()
    other_id = uuid7()
    now = datetime.now(UTC)

    default_in_memory_sse_job_store.clear()

    async with async_session_factory() as session:
        u1 = UserORM(
            id=owner_id,
            email=f"plan_owner_{owner_id.hex[:8]}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="Planning Owner Learner",
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE",
            is_locked=False,
        )
        u2 = UserORM(
            id=other_id,
            email=f"plan_other_{other_id.hex[:8]}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="Other Learner",
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE",
            is_locked=False,
        )
        q1 = AIQuotaORM(
            id=uuid7(),
            user_id=owner_id,
            free_credits_remaining=5,
            paid_credits_remaining=2,
            used_calls=0,
            reserved_calls=0,
            tokens_consumed=0,
            cycle_start=now,
            cycle_end=now + timedelta(days=30),
        )
        q2 = AIQuotaORM(
            id=uuid7(),
            user_id=other_id,
            free_credits_remaining=5,
            paid_credits_remaining=0,
            used_calls=0,
            reserved_calls=0,
            tokens_consumed=0,
            cycle_start=now,
            cycle_end=now + timedelta(days=30),
        )
        session.add_all([u1, u2])
        await session.flush()
        session.add_all([q1, q2])
        await session.commit()

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_learner_id] = lambda: owner_id

    try:
        yield owner_id, other_id
    finally:
        app.dependency_overrides.clear()
        default_in_memory_sse_job_store.clear()
        async with async_session_factory() as session:
            await session.execute(delete(UserORM).where(UserORM.id.in_([owner_id, other_id])))
            await session.commit()


@pytest.mark.asyncio
async def test_e2e_ai_planning_flow_sse_approval_edit_soft_overflow_and_os03_merge(
    planning_users: tuple[UUID, UUID],
) -> None:
    """Full End-to-End Integration Test covering Phase 3 & Phase 4:
    1. Create Roadmap (`POST /api/v1/roadmaps`) -> 201 Created.
    2. Guard FR-PLAN-001: Generating Level-2 Proposal before Milestones are APPROVED -> 409 UNAPPROVED_MILESTONES.
    3. Generate Level-1 Milestones (`POST .../milestones/generate-jobs`) with Idempotency-Key deduplication
       -> 202 Accepted + SSE stream (`GET /api/v1/roadmaps/jobs/{job_id}/stream`) + Last-Event-ID replay.
    4. Edit & Reorder Milestones (`PUT .../milestones`) and Approve (`POST .../milestones/approve`)
       -> emits MilestoneApprovedEvent in `outbox_events`.
    5. Generate Level-2 Schedule Proposal (`POST .../proposals/generate-jobs`) with Self-Correction Retry
       (1st attempt fails Tier 1 duration, 2nd attempt succeeds) -> SSE emits `validation_retry` & `completed`.
    6. Preview (`GET .../proposals/current`) & Edit Proposal (`PUT .../proposals/{id}`).
    7. Mode B Soft Overflow <= 30m Confirmation Gate on Apply (`409 SOFT_OVERFLOW_CONFIRMATION_REQUIRED`
       when `confirm_soft_overflow=False`, `200 OK` when `confirm_soft_overflow=True`).
    8. OS-03 Merge / Future Shift on Re-plan Apply preserving `COMPLETED` tasks from the past.
    9. Portfolio endpoints (`GET /api/v1/roadmaps`, `GET /api/v1/roadmaps/{id}`, `PATCH`, `POST .../archive`).
    """
    owner_id, _ = planning_users
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Goal & Roadmap
        create_res = await client.post(
            "/api/v1/roadmaps",
            json={
                "title": "Lộ trình Thiết kế Hệ thống Phân tán",
                "description": "Chinh phục Consensus, Outbox và Event-Driven Architecture",
                "start_date": "2026-11-02",
                "target_date": "2026-12-15",
            },
        )
        assert create_res.status_code == 201
        roadmap_data = create_res.json()
        roadmap_id = UUID(roadmap_data["id"])
        assert roadmap_data["status"] == "INITIALIZED"
        assert roadmap_data["goal"]["title"] == "Lộ trình Thiết kế Hệ thống Phân tán"

        # 2. Attempt Level-2 Proposal generation before milestones are approved -> 409
        premature_res = await client.post(f"/api/v1/roadmaps/{roadmap_id}/proposals/generate-jobs")
        assert premature_res.status_code == 409
        assert premature_res.json()["code"] == "UNAPPROVED_MILESTONES"

        # 3. Generate Level-1 Milestones via 2-Stage SSE + Idempotency-Key deduplication
        ms_job_res1 = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/milestones/generate-jobs",
            headers={"Idempotency-Key": "ms-gen-key-1"},
        )
        assert ms_job_res1.status_code == 202
        ticket1 = ms_job_res1.json()
        job1_id = ticket1["job_id"]
        assert ticket1["jobId"] == job1_id
        assert ticket1["streamUrl"] == f"/api/v1/roadmaps/jobs/{job1_id}/stream"

        # Repeated POST with same Idempotency-Key returns exact same job_id without extra quota deduction
        ms_job_res2 = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/milestones/generate-jobs",
            headers={"Idempotency-Key": "ms-gen-key-1"},
        )
        assert ms_job_res2.status_code == 202
        assert ms_job_res2.json()["job_id"] == job1_id

        # Stream SSE events and verify Last-Event-ID replay
        sse_res = await client.get(ticket1["stream_url"])
        assert sse_res.status_code == 200
        assert "text/event-stream" in sse_res.headers["content-type"]
        assert "event: stage" in sse_res.text
        assert "event: completed" in sse_res.text

        replay_res = await client.get(
            ticket1["stream_url"],
            headers={"Last-Event-ID": "2"},
        )
        assert replay_res.status_code == 200
        assert "id: 1\n" not in replay_res.text
        assert "event: completed" in replay_res.text

        # 4. Edit Milestones (`PUT .../milestones`) & Approve (`POST .../milestones/approve`)
        detail_before = (await client.get(f"/api/v1/roadmaps/{roadmap_id}")).json()
        generated_ms = detail_before["milestones"]
        assert len(generated_ms) == 3
        assert all(m["status"] == "PENDING" for m in generated_ms)

        put_ms_res = await client.put(
            f"/api/v1/roadmaps/{roadmap_id}/milestones",
            json={
                "milestones": [
                    {
                        "id": generated_ms[0]["id"],
                        "sequence_order": 1,
                        "title": "Chặng 1: Nền tảng Hệ phân tán & Clock",
                        "description": "Logical clocks & Lamport timestamps",
                    },
                    {
                        "id": generated_ms[1]["id"],
                        "sequence_order": 2,
                        "title": "Chặng 2: Raft Consensus & Replication",
                        "description": "Leader election & log replication",
                    },
                    {
                        "id": generated_ms[2]["id"],
                        "sequence_order": 3,
                        "title": "Chặng 3: Transactional Outbox & Saga",
                        "description": "Đảm bảo At-least-once delivery",
                    },
                ]
            },
        )
        assert put_ms_res.status_code == 200
        updated_ms = put_ms_res.json()["milestones"]
        m1_id = updated_ms[0]["id"]
        m2_id = updated_ms[1]["id"]

        approve_res = await client.post(f"/api/v1/roadmaps/{roadmap_id}/milestones/approve")
        assert approve_res.status_code == 200
        approved_ms = approve_res.json()["milestones"]
        assert all(m["status"] == "APPROVED" for m in approved_ms)

        # Verify MilestoneApprovedEvent in outbox_events
        async with async_session_factory() as session:
            outbox_ms = list(
                (
                    await session.execute(
                        select(OutboxEventORM).where(
                            OutboxEventORM.aggregate_id == roadmap_id,
                            OutboxEventORM.event_type == "MilestoneApprovedEvent",
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(outbox_ms) == 1

        # 5. Switch learner to Mode B with Monday 19:00-21:00 slot to test Soft Overflow & Retry
        from datetime import time

        async with async_session_factory() as session:
            avail_id = uuid7()
            avail = AvailabilityORM(
                id=avail_id,
                user_id=owner_id,
                mode="MODE_B",
                calendar_integration_mode="NONE",
                min_session_minutes=30,
                daily_quotas={"monday": {"enabled": True, "quota_hours": 2.0}},
            )
            slot = AvailabilitySlotORM(
                id=uuid7(),
                availability_id=avail_id,
                day_of_week=0,  # Monday
                slot_type="FIXED",
                start_time=time(19, 0),
                end_time=time(21, 0),
                end_day_offset=0,
                is_active=True,
            )
            session.add(avail)
            await session.flush()
            session.add(slot)
            await session.commit()

        # Configure MockLLMAdapter so Attempt 1 has an invalid 15m AI task (< 30m Tier 1 bound),
        # and Attempt 2 self-corrects to valid tasks with a 20m Soft Overflow (19:00-20:00 and 20:00-21:20)
        t1_id = str(uuid7())
        t2_id = str(uuid7())
        canned_llm = MockLLMAdapter(
            canned_responses=[
                {
                    "tasks": [
                        {
                            "task_id": t1_id,
                            "milestone_id": m1_id,
                            "title": "Task lỗi Tier 1 (15m < 30m)",
                            "estimated_minutes": 15,
                            "scheduled_date": "2026-11-02",
                            "scheduled_start": "2026-11-02T19:00:00+00:00",
                            "scheduled_end": "2026-11-02T19:15:00+00:00",
                        }
                    ],
                    "dependencies": [],
                },
                {
                    "tasks": [
                        {
                            "task_id": t1_id,
                            "milestone_id": m1_id,
                            "title": "Đọc bài báo Lamport Clock",
                            "estimated_minutes": 60,
                            "scheduled_date": "2026-11-02",
                            "scheduled_start": "2026-11-02T19:00:00+00:00",
                            "scheduled_end": "2026-11-02T20:00:00+00:00",
                        },
                        {
                            "task_id": t2_id,
                            "milestone_id": m2_id,
                            "title": "Thực hành Raft Leader Election (Soft Overflow 20p)",
                            "estimated_minutes": 80,
                            "scheduled_date": "2026-11-02",
                            "scheduled_start": "2026-11-02T20:00:00+00:00",
                            "scheduled_end": "2026-11-02T21:20:00+00:00",
                        },
                    ],
                    "dependencies": [
                        {
                            "predecessor_id": t1_id,
                            "successor_id": t2_id,
                            "is_mandatory": True,
                        }
                    ],
                },
            ]
        )
        app.dependency_overrides[get_llm_provider] = lambda: canned_llm

        prop_job_res = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/generate-jobs",
            headers={"Idempotency-Key": "prop-gen-key-1"},
        )
        assert prop_job_res.status_code == 202
        prop_ticket = prop_job_res.json()

        prop_sse = await client.get(prop_ticket["stream_url"])
        assert prop_sse.status_code == 200
        assert "event: validation_retry" in prop_sse.text
        assert "event: completed" in prop_sse.text

        # 6. Get Current Proposal (`GET .../proposals/current`)
        curr_prop_res = await client.get(f"/api/v1/roadmaps/{roadmap_id}/proposals/current")
        assert curr_prop_res.status_code == 200
        curr_prop = curr_prop_res.json()
        proposal_id = curr_prop["id"]
        assert curr_prop["status"] == "DRAFT"
        assert curr_prop["has_soft_overflow"] is True
        assert curr_prop["soft_overflow_warnings"][0]["overflow_minutes"] == 20

        # 7. Apply without confirm_soft_overflow -> 409 SOFT_OVERFLOW_CONFIRMATION_REQUIRED
        apply_no_confirm = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{proposal_id}/apply",
            json={"confirm_soft_overflow": False},
        )
        assert apply_no_confirm.status_code == 409
        assert apply_no_confirm.json()["code"] == "SOFT_OVERFLOW_CONFIRMATION_REQUIRED"

        # Apply WITH confirm_soft_overflow=True -> 200 OK
        apply_ok = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{proposal_id}/apply",
            json={"confirm_soft_overflow": True},
        )
        assert apply_ok.status_code == 200
        apply_data = apply_ok.json()
        assert apply_data["roadmap_status"] == "ACTIVE"
        assert apply_data["proposal_status"] == "APPLIED"
        assert apply_data["total_sessions"] == 2
        assert apply_data["total_planned_minutes"] == 140
        assert apply_data["trigger_type"] == "INITIAL_APPLY"

        # 8. Mark Task 1 as COMPLETED in DB, then create & edit a new Proposal and Apply to verify OS-03 Merge
        async with async_session_factory() as session:
            t1_orm = await session.get(TaskORM, UUID(t1_id))
            assert t1_orm is not None
            t1_orm.status = "COMPLETED"
            t1_orm.completed_at = datetime.now(UTC)
            await session.commit()

        # Use manual/edit flow to create a new DRAFT proposal and edit it with a 15-minute task (valid in manual [15, 240]m)
        t3_id = str(uuid7())
        manual_replan_res = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/manual",
            json={
                "tasks": [
                    {
                        "task_id": t3_id,
                        "milestone_id": m2_id,
                        "title": "Ôn tập nhanh Outbox Relay (15 phút thủ công)",
                        "estimated_minutes": 15,
                        "scheduled_date": "2026-11-09",
                        "scheduled_start": "2026-11-09T19:00:00+00:00",
                        "scheduled_end": "2026-11-09T19:15:00+00:00",
                    }
                ],
                "dependencies": [],
            },
        )
        assert manual_replan_res.status_code == 201
        replan_prop_id = manual_replan_res.json()["id"]

        # Edit proposal (`PUT .../proposals/{proposal_id}`) to 45 minutes
        edit_prop_res = await client.put(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{replan_prop_id}",
            json={
                "tasks": [
                    {
                        "task_id": t3_id,
                        "milestone_id": m2_id,
                        "title": "Cài đặt hoàn chỉnh Outbox Relay (45 phút)",
                        "estimated_minutes": 45,
                        "scheduled_date": "2026-11-09",
                        "scheduled_start": "2026-11-09T19:00:00+00:00",
                        "scheduled_end": "2026-11-09T19:45:00+00:00",
                    }
                ],
                "dependencies": [
                    {
                        "predecessor_id": t1_id,
                        "successor_id": t3_id,
                        "is_mandatory": True,
                    }
                ],
            },
        )
        assert edit_prop_res.status_code == 200
        assert edit_prop_res.json()["is_valid"] is True

        # Apply Replan -> OS-03 Merge preserves COMPLETED t1_id, replaces TODO t2_id, inserts t3_id
        apply_replan = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{replan_prop_id}/apply",
            json={"confirm_soft_overflow": False},
        )
        assert apply_replan.status_code == 200
        replan_data = apply_replan.json()
        assert replan_data["preserved_completed_tasks_count"] == 1
        assert replan_data["replaced_tasks_count"] == 1
        assert replan_data["inserted_tasks_count"] == 1
        assert replan_data["total_sessions"] == 2
        assert replan_data["total_planned_minutes"] == 105  # 60m completed + 45m new
        assert replan_data["trigger_type"] == "REPLAN_MERGE"

        # 9. Get Roadmap Detail & Archive
        detail_after = await client.get(f"/api/v1/roadmaps/{roadmap_id}")
        assert detail_after.status_code == 200
        detail_json = detail_after.json()
        assert detail_json["status"] == "ACTIVE"
        assert len(detail_json["scheduled_tasks"]) == 2
        assert detail_json["official_schedule"]["total_planned_minutes"] == 105

        list_res = await client.get("/api/v1/roadmaps?status=ACTIVE")
        assert list_res.status_code == 200
        assert len(list_res.json()) == 1

        patch_res = await client.patch(
            f"/api/v1/roadmaps/{roadmap_id}",
            json={"title": "Lộ trình Hệ thống Phân tán (Đã cập nhật)", "status": "PAUSED"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "PAUSED"

        archive_res = await client.post(f"/api/v1/roadmaps/{roadmap_id}/archive")
        assert archive_res.status_code == 200
        assert archive_res.json()["status"] == "ARCHIVED"

        # Verify schedule_change_logs has 2 entries (INITIAL_APPLY & REPLAN_MERGE)
        async with async_session_factory() as session:
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
            assert len(logs) == 2

            reservations = list(
                (
                    await session.execute(
                        select(AIQuotaReservationORM).where(
                            AIQuotaReservationORM.user_id == owner_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(reservations) == 2
            assert all(r.status == "COMMITTED" for r in reservations)

            deps_in_db = list(
                (
                    await session.execute(
                        select(TaskDependencyORM).where(TaskDependencyORM.roadmap_id == roadmap_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(deps_in_db) == 1
            assert deps_in_db[0].predecessor_id == UUID(t1_id)
            assert deps_in_db[0].successor_id == UUID(t3_id)


@pytest.mark.asyncio
async def test_manual_planning_uc09_zero_ai_quota_and_idor_404_protection(
    planning_users: tuple[UUID, UUID],
) -> None:
    """Verify:
    1. Manual Roadmap Planning (`UC-09`, `POST /api/v1/roadmaps/{id}/proposals/manual`) creates
       APPROVED Milestones and a DRAFT ScheduleProposal with 0 AI Quota consumed.
    2. IDOR protection (`NFR-SEC-004`): accessing another user's roadmap or SSE job returns `404 Not Found`.
    """
    owner_id, other_id = planning_users
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Roadmap as owner_id
        create_res = await client.post(
            "/api/v1/roadmaps",
            json={
                "title": "Lộ trình Tự học Rust Thủ công (UC-09)",
                "start_date": "2026-11-02",
                "target_date": "2026-11-30",
            },
        )
        assert create_res.status_code == 201
        roadmap_id = UUID(create_res.json()["id"])

        # 2. Save manual plan (milestones + tasks) without calling AI
        manual_res = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/manual",
            json={
                "milestones": [
                    {
                        "sequence_order": 1,
                        "title": "Ownership & Borrowing",
                        "description": "Nắm vững bộ kiểm tra mượn của Rust",
                    }
                ],
                "tasks": [
                    {
                        "milestone_sequence_order": 1,
                        "title": "Làm bài tập Rustlings phần Ownership",
                        "estimated_minutes": 90,
                        "scheduled_date": date(2026, 11, 2).isoformat(),
                    }
                ],
                "dependencies": [],
            },
        )
        assert manual_res.status_code == 201
        proposal_id = manual_res.json()["id"]

        # Verify 0 AI Quota consumed (free_credits_remaining is still 5, used_calls is 0)
        async with async_session_factory() as session:
            quota = (
                await session.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == owner_id))
            ).scalar_one()
            assert quota.free_credits_remaining == 5
            assert quota.used_calls == 0

        # 3. Switch authenticated user to `other_id` and verify IDOR 404 on all endpoints
        app.dependency_overrides[get_current_learner_id] = lambda: other_id

        r_detail = await client.get(f"/api/v1/roadmaps/{roadmap_id}")
        assert r_detail.status_code == 404

        r_ms = await client.post(f"/api/v1/roadmaps/{roadmap_id}/milestones/generate-jobs")
        assert r_ms.status_code == 404

        r_curr = await client.get(f"/api/v1/roadmaps/{roadmap_id}/proposals/current")
        assert r_curr.status_code == 404

        r_apply = await client.post(f"/api/v1/roadmaps/{roadmap_id}/proposals/{proposal_id}/apply")
        assert r_apply.status_code == 404

        r_archive = await client.post(f"/api/v1/roadmaps/{roadmap_id}/archive")
        assert r_archive.status_code == 404
