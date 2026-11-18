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
from src.account.infrastructure.orm.user_orm import AIQuotaORM, UserORM
from src.account.presentation.deps import get_current_learner_id
from src.main import app
from src.planning.infrastructure.orm.planning_orm import MilestoneORM, ScheduleProposalORM
from src.planning.presentation.deps import get_llm_provider
from src.planning.presentation.tasks import consume_availability_updated_event
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM, ProcessedEventORM
from src.shared_kernel.infrastructure.sse import default_in_memory_sse_job_store
from tests.helpers.llm_stubs import StubLLMAdapter


@pytest.fixture
async def pr_b_user() -> AsyncGenerator[UUID, None]:
    user_id = uuid7()
    now = datetime.now(UTC)
    default_in_memory_sse_job_store.clear()

    async with async_session_factory() as session:
        user = UserORM(
            id=user_id,
            email=f"prb_owner_{user_id.hex}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="PR-B FIT_CAPACITY Learner",
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
        avail_id = uuid7()
        # Tight capacity: Monday 19:00-21:00 (120m/week -> 240m over 2 Mondays)
        avail = AvailabilityORM(
            id=avail_id,
            user_id=user_id,
            mode="MODE_B",
            calendar_integration_mode="NONE",
            min_session_minutes=30,
            daily_quotas={"monday": {"enabled": True, "quota_hours": 2.0}},
        )
        slot = AvailabilitySlotORM(
            id=uuid7(),
            availability_id=avail_id,
            day_of_week=0,
            slot_type="FIXED",
            start_time=time(19, 0),
            end_time=time(21, 0),
            end_day_offset=0,
            is_active=True,
        )
        session.add(user)
        await session.flush()
        session.add_all([quota, avail])
        await session.flush()
        session.add(slot)
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
                delete(OutboxEventORM).where(OutboxEventORM.aggregate_id == user_id)
            )
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()


def _parse_sse_completed_payload(sse_text: str) -> dict[str, Any]:
    for block in sse_text.split("\n\n"):
        if "event: completed" in block:
            for line in block.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[len("data:") :].strip())  # type: ignore[no-any-return]
    return {}


def test_def05_openapi_exposes_typed_409_planning_conflict_response() -> None:
    schema = app.openapi()
    components = schema.get("components", {}).get("schemas", {})
    assert "PlanningConflictResponse" in components
    conflict_props = components["PlanningConflictResponse"]["properties"]
    for required_prop in (
        "code",
        "message",
        "detail",
        "scope_proposal_version",
        "scope_proposal_hash",
        "preliminary_feasibility",
        "hard_packable_capacity_minutes",
        "conflicts",
        "overflow_minutes",
        "soft_overflow_warnings",
        "judge_status",
        "advisory_warnings",
        "schedulable_ratio",
    ):
        assert required_prop in conflict_props

    paths = schema["paths"]
    expected_409_ops = [
        ("/api/v1/roadmaps/{roadmap_id}/milestones/approve", "post"),
        ("/api/v1/roadmaps/{roadmap_id}/milestones", "put"),
        ("/api/v1/roadmaps/{roadmap_id}/proposals/generate-jobs", "post"),
        ("/api/v1/roadmaps/{roadmap_id}/proposals/{proposal_id}/apply", "post"),
        ("/api/v1/roadmaps/{roadmap_id}/proposals/{proposal_id}", "put"),
    ]
    for path, method in expected_409_ops:
        responses = paths[path][method]["responses"]
        assert "409" in responses, f"Missing 409 response schema on {method.upper()} {path}"


@pytest.mark.asyncio
async def test_e2e_pr_b_fit_capacity_roundtrip_and_staleness_invalidation(
    pr_b_user: UUID,
) -> None:
    transport = ASGITransport(app=app)
    three_milestones_llm = {
        "milestones": [
            {
                "sequence_order": 1,
                "title": "Nền tảng Rust Ownership",
                "description": "Cài đặt và kiểm thử ownership",
                "learning_outcomes": ["Hiểu ownership", "Kiểm thử unit"],
                "completion_criteria": "Pass unit test",
                "estimated_effort_minutes": 180,
                "required_concepts": [],
                "unverified_concepts": ["rust-ownership"],
                "dependencies": [],
            },
            {
                "sequence_order": 2,
                "title": "Async Tokio & Channels",
                "description": "Xây dựng server async",
                "learning_outcomes": ["Triển khai channel", "Kiểm thử tích hợp"],
                "completion_criteria": "Server async chạy ổn định",
                "estimated_effort_minutes": 240,
                "required_concepts": [],
                "unverified_concepts": ["tokio"],
                "dependencies": [1],
            },
            {
                "sequence_order": 3,
                "title": "Đồ án Raft Cluster",
                "description": "Xây dựng cụm Raft 3-node",
                "learning_outcomes": ["Triển khai leader election", "Chạy chaos test"],
                "completion_criteria": "Đồ án cụm 3-node vượt qua chaos test",
                "estimated_effort_minutes": 360,
                "required_concepts": [],
                "unverified_concepts": ["raft"],
                "dependencies": [2],
            },
        ],
        "scope_summary": "FULL_SCOPE",
        "deferred_scope": [],
    }
    app.dependency_overrides[get_llm_provider] = lambda: StubLLMAdapter(
        canned_responses=[three_milestones_llm]
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create roadmap spanning 2 Mondays (240m P_hard)
        create_res = await client.post(
            "/api/v1/roadmaps",
            json={
                "title": "PR-B FIT_CAPACITY E2E",
                "description": "Kiểm thử end-to-end FIT_CAPACITY",
                "start_date": "2026-11-02",
                "target_date": "2026-11-15",
            },
        )
        assert create_res.status_code == 201
        roadmap_id = UUID(create_res.json()["id"])

        # 2. Generate milestones -> FIT_CAPACITY_REQUIRES_APPROVAL
        ms_job = await client.post(f"/api/v1/roadmaps/{roadmap_id}/milestones/generate-jobs")
        assert ms_job.status_code == 202
        ms_sse = await client.get(ms_job.json()["stream_url"])
        assert "event: completed" in ms_sse.text
        ms_completed = _parse_sse_completed_payload(ms_sse.text)
        prelim_v1 = ms_completed["payload"]["preliminary_feasibility"]
        assert prelim_v1["status"] == "FIT_CAPACITY_REQUIRES_APPROVAL"
        assert prelim_v1["scope_proposal_version"] == 1
        assert len(prelim_v1["deferred_scope"]) >= 1

        # 3. Approve without confirm -> 409 SCOPE_APPROVAL_REQUIRED
        unconfirmed_approve = await client.post(f"/api/v1/roadmaps/{roadmap_id}/milestones/approve")
        assert unconfirmed_approve.status_code == 409
        assert unconfirmed_approve.json()["code"] == "SCOPE_APPROVAL_REQUIRED"
        assert unconfirmed_approve.json()["scope_proposal_version"] == 1

        # 4. Approve with matching version -> 200 OK with preliminary_feasibility (DEF-05)
        ok_approve = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/milestones/approve",
            json={"confirmed_scope_proposal_version": 1, "accept_fit_capacity": True},
        )
        assert ok_approve.status_code == 200, ok_approve.text
        approve_json = ok_approve.json()
        assert approve_json["preliminary_feasibility"] is not None
        assert (
            approve_json["preliminary_feasibility"]["scope_approval_status"]
            == "APPROVED_BY_LEARNER"
        )
        kept_ms = [m for m in approve_json["milestones"] if m["status"] == "APPROVED"]
        deferred_ms = [m for m in approve_json["milestones"] if m["status"] == "PENDING"]
        assert len(kept_ms) >= 1
        assert len(deferred_ms) >= 1

        # Double-submit approve -> 200 OK idempotent
        double_approve = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/milestones/approve",
            json={"confirmed_scope_proposal_version": 1, "accept_fit_capacity": True},
        )
        assert double_approve.status_code == 200

        # 5. Generate proposal (ONLY kept milestones)
        app.dependency_overrides[get_llm_provider] = lambda: StubLLMAdapter()
        prop_job = await client.post(f"/api/v1/roadmaps/{roadmap_id}/proposals/generate-jobs")
        assert prop_job.status_code == 202
        prop_sse = await client.get(prop_job.json()["stream_url"])
        assert "event: completed" in prop_sse.text

        curr = await client.get(f"/api/v1/roadmaps/{roadmap_id}/proposals/current")
        assert curr.status_code == 200
        proposal_json = curr.json()
        proposal_id = proposal_json["id"]

        # 6. DEF-01: UpdateProposal MUST succeed without 422 MILESTONE_WITHOUT_TASKS on deferred PENDING milestone
        edited_tasks = [dict(t) for t in proposal_json["tasks"]]
        edited_tasks[0]["title"] = "Bài 1 (chỉnh sửa): Rust Ownership"
        upd_prop_res = await client.put(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{proposal_id}",
            json={
                "tasks": edited_tasks,
                "dependencies": proposal_json["dependencies"],
                "reject_invalid": True,
            },
        )
        assert upd_prop_res.status_code == 200, upd_prop_res.text

        # 7. DEF-01: ApplyProposal MUST succeed without 422 MILESTONE_WITHOUT_TASKS
        apply_res = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{proposal_id}/apply",
            json={"confirm_warnings": True, "confirm_partial_schedule": True},
        )
        assert apply_res.status_code == 200, apply_res.text

        # Deferred milestones stay PENDING in DB
        async with async_session_factory() as session:
            db_ms = list(
                (
                    await session.execute(
                        select(MilestoneORM).where(MilestoneORM.roadmap_id == roadmap_id)
                    )
                )
                .scalars()
                .all()
            )
            for m in db_ms:
                if str(m.id) in {dm["id"] for dm in deferred_ms}:
                    assert m.status == "PENDING"

        # 8. DEF-05 & DEF-06: PUT /milestones recomputes preliminary_feasibility, discards DRAFT, resets approval
        prop_job2 = await client.post(f"/api/v1/roadmaps/{roadmap_id}/proposals/generate-jobs")
        assert prop_job2.status_code == 202
        await client.get(prop_job2.json()["stream_url"])

        put_ms_res = await client.put(
            f"/api/v1/roadmaps/{roadmap_id}/milestones",
            json={
                "milestones": [
                    {
                        "id": m["id"],
                        "sequence_order": m["sequence_order"],
                        "title": m["title"],
                        "description": m.get("description") or "",
                        "learning_outcomes": m.get("learning_outcomes") or [],
                        "completion_criteria": "Tiêu chí mới cho cột mốc",
                        "estimated_effort_minutes": 240
                        if idx == 0
                        else m["estimated_effort_minutes"],
                        "prerequisite_milestone_ids": m.get("prerequisite_milestone_ids") or [],
                    }
                    for idx, m in enumerate(approve_json["milestones"])
                ]
            },
        )
        assert put_ms_res.status_code == 200, put_ms_res.text
        put_ms_json = put_ms_res.json()
        assert put_ms_json["preliminary_feasibility"] is not None
        assert (
            put_ms_json["preliminary_feasibility"]["scope_approval_status"]
            == "PENDING_LEARNER_APPROVAL"
        )
        v_after_edit = put_ms_json["preliminary_feasibility"]["scope_proposal_version"]
        assert v_after_edit >= 2

        # DRAFT was discarded
        async with async_session_factory() as session:
            drafts = list(
                (
                    await session.execute(
                        select(ScheduleProposalORM).where(
                            ScheduleProposalORM.roadmap_id == roadmap_id,
                            ScheduleProposalORM.status == "DRAFT",
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(drafts) == 0

        # Cannot generate proposal until re-approved
        blocked_prop = await client.post(f"/api/v1/roadmaps/{roadmap_id}/proposals/generate-jobs")
        assert blocked_prop.status_code == 409
        assert blocked_prop.json()["code"] == "SCOPE_APPROVAL_REQUIRED"

        # 9. Re-approve, then PATCH /roadmaps/{id} target_date invalidates again
        reapprove = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/milestones/approve",
            json={"confirmed_scope_proposal_version": v_after_edit, "accept_fit_capacity": True},
        )
        assert reapprove.status_code == 200

        patch_rm = await client.patch(
            f"/api/v1/roadmaps/{roadmap_id}",
            json={"target_date": "2026-11-10"},
        )
        assert patch_rm.status_code == 200
        patch_prelim = patch_rm.json()["preliminary_feasibility"]
        assert patch_prelim["scope_approval_status"] == "PENDING_LEARNER_APPROVAL"

        # 10. Re-approve latest version, then shrink availability via PUT /availabilities/me -> sync drift catches 409!
        v_after_patch = patch_prelim["scope_proposal_version"]
        reapprove2 = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/milestones/approve",
            json={"confirmed_scope_proposal_version": v_after_patch, "accept_fit_capacity": True},
        )
        assert reapprove2.status_code == 200

        avail_update = await client.put(
            "/api/v1/availabilities/me",
            json={
                "mode": "MODE_B",
                "calendar_integration_mode": "NONE",
                "min_session_minutes": 30,
                "weekly_schedule": {
                    "monday": {
                        "enabled": True,
                        "quota_hours": 1.0,
                        "time_slots": [{"start": "19:00", "end": "20:00"}],
                    },
                    "tuesday": {"enabled": False, "quota_hours": 0, "time_slots": []},
                    "wednesday": {"enabled": False, "quota_hours": 0, "time_slots": []},
                    "thursday": {"enabled": False, "quota_hours": 0, "time_slots": []},
                    "friday": {"enabled": False, "quota_hours": 0, "time_slots": []},
                    "saturday": {"enabled": False, "quota_hours": 0, "time_slots": []},
                    "sunday": {"enabled": False, "quota_hours": 0, "time_slots": []},
                },
            },
        )
        assert avail_update.status_code == 200, avail_update.text

        # Without even running background worker, synchronous drift check MUST catch stale approval!
        stale_gen = await client.post(f"/api/v1/roadmaps/{roadmap_id}/proposals/generate-jobs")
        assert stale_gen.status_code == 409
        assert stale_gen.json()["code"] in ("SCOPE_APPROVAL_REQUIRED", "PRELIMINARY_UNSCHEDULABLE")

        # 11. Outbox consumer idempotency: poll_planning_outbox_events processes AvailabilityUpdatedEvent once
        # Seed a fresh AvailabilityUpdatedEvent by updating availability slightly (Monday 1.5h)
        avail_update2 = await client.put(
            "/api/v1/availabilities/me",
            json={
                "mode": "MODE_B",
                "calendar_integration_mode": "NONE",
                "min_session_minutes": 30,
                "weekly_schedule": {
                    "monday": {
                        "enabled": True,
                        "quota_hours": 1.5,
                        "time_slots": [{"start": "19:00", "end": "20:30"}],
                    },
                    "tuesday": {"enabled": False, "quota_hours": 0, "time_slots": []},
                    "wednesday": {"enabled": False, "quota_hours": 0, "time_slots": []},
                    "thursday": {"enabled": False, "quota_hours": 0, "time_slots": []},
                    "friday": {"enabled": False, "quota_hours": 0, "time_slots": []},
                    "saturday": {"enabled": False, "quota_hours": 0, "time_slots": []},
                    "sunday": {"enabled": False, "quota_hours": 0, "time_slots": []},
                },
            },
        )
        assert avail_update2.status_code == 200
        async with async_session_factory() as session:
            ev_rows = list(
                (
                    await session.execute(
                        select(OutboxEventORM)
                        .where(
                            OutboxEventORM.event_type == "AvailabilityUpdatedEvent",
                        )
                        .order_by(OutboxEventORM.created_at.desc())
                    )
                )
                .scalars()
                .all()
            )
            user_events = [
                ev for ev in ev_rows if str((ev.payload or {}).get("user_id")) == str(pr_b_user)
            ]
            assert len(user_events) >= 1
            latest_ev_id = user_events[0].id

        processed_1 = await consume_availability_updated_event(
            event_id=str(latest_ev_id),
            user_id=str(pr_b_user),
        )
        assert processed_1 == 1
        processed_2 = await consume_availability_updated_event(
            event_id=str(latest_ev_id),
            user_id=str(pr_b_user),
        )
        assert processed_2 == 0

        async with async_session_factory() as session:
            pe_rows = list(
                (
                    await session.execute(
                        select(ProcessedEventORM).where(
                            ProcessedEventORM.event_id == latest_ev_id,
                            ProcessedEventORM.handler_name
                            == "planning.availability_updated_consumer",
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(pe_rows) == 1
