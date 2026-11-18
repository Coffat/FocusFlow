from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, time, timedelta
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
from src.execution.infrastructure.orm.session_orm import StudySessionORM
from src.execution.infrastructure.orm.task_orm import TaskDependencyORM, TaskORM
from src.main import app
from src.planning.infrastructure.orm.planning_orm import ScheduleBlockORM
from src.planning.presentation.deps import get_llm_provider
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM
from src.shared_kernel.infrastructure.sse import default_in_memory_sse_job_store
from tests.helpers.llm_stubs import StubLLMAdapter


@pytest.fixture
async def pr_c_user() -> AsyncGenerator[UUID, None]:
    user_id = uuid7()
    now = datetime.now(UTC)
    default_in_memory_sse_job_store.clear()

    async with async_session_factory() as session:
        user = UserORM(
            id=user_id,
            email=f"prc_owner_{user_id.hex}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="PR-C Reoptimize Learner",
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
        profile = LearnerProfileORM(
            id=uuid7(),
            user_id=user_id,
            opt_session_minutes=60,
            estimation_bias_beta=1.5,
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
                "wednesday": {"enabled": True, "quota_hours": 2.0},
                "friday": {"enabled": True, "quota_hours": 2.0},
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
            for dow in (0, 2, 4)  # Mon, Wed, Fri
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


@pytest.mark.asyncio
async def test_e2e_pr_c_reoptimize_and_overdue_recovery_postgres_roundtrip(
    pr_c_user: UUID,
) -> None:
    """Full PostgreSQL roundtrip for DEF-02: metadata, DAG deps + UUID rotation, protected blocks, COMPLETED tasks, beta=1.5."""
    user_id = pr_c_user
    transport = ASGITransport(app=app)

    today_vn = datetime.now(UTC).date()
    start_date = today_vn - timedelta(days=14)
    target_date = today_vn + timedelta(days=30)

    canned_milestones = {
        "milestones": [
            {
                "sequence_order": 1,
                "title": "Chặng 1: Cú pháp Python",
                "description": "Biến và kiểu dữ liệu cơ bản",
                "learning_outcomes": ["Hiểu biến Python"],
                "completion_criteria": "Pass quiz biến Python",
                "estimated_effort_minutes": 90,
                "required_concepts": ["py-syntax-variables"],
                "unverified_concepts": [],
                "dependencies": [],
            },
            {
                "sequence_order": 2,
                "title": "Chặng 2: Điều khiển & Hàm",
                "description": "Vòng lặp, hàm và kiểm thử",
                "learning_outcomes": ["Viết hàm chuẩn", "Viết unit test"],
                "completion_criteria": "Pass bài thực hành hàm",
                "estimated_effort_minutes": 360,
                "required_concepts": ["py-control-flow-functions"],
                "unverified_concepts": [],
                "dependencies": [1],
            },
        ],
        "scope_summary": "FULL_SCOPE",
        "deferred_scope": [],
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create roadmap & approve milestones
        create_res = await client.post(
            "/api/v1/roadmaps",
            json={
                "title": "PR-C Reoptimize E2E",
                "description": "Kiểm thử PostgreSQL roundtrip DEF-02",
                "start_date": start_date.isoformat(),
                "target_date": target_date.isoformat(),
            },
        )
        assert create_res.status_code == 201
        roadmap_id = UUID(create_res.json()["id"])

        app.dependency_overrides[get_llm_provider] = lambda: StubLLMAdapter(
            canned_responses=[canned_milestones]
        )
        ms_job = await client.post(f"/api/v1/roadmaps/{roadmap_id}/milestones/generate-jobs")
        assert ms_job.status_code == 202
        ms_sse = await client.get(ms_job.json()["stream_url"])
        assert "event: completed" in ms_sse.text

        approve_res = await client.post(f"/api/v1/roadmaps/{roadmap_id}/milestones/approve")
        assert approve_res.status_code == 200, approve_res.text
        milestones = sorted(approve_res.json()["milestones"], key=lambda m: m["sequence_order"])
        m1_id = milestones[0]["id"]
        m2_id = milestones[1]["id"]

        # 2. Generate & apply initial schedule WITH T0(M1) -> T1(M2, 60m*1.5=90m) -> T2(M2, 60m*1.5=90m), plus T3(M2, future)
        t0_id = str(uuid7())
        t1_id = str(uuid7())
        t2_id = str(uuid7())
        t3_id = str(uuid7())
        canned_tasks = {
            "tasks": [
                {
                    "task_id": t0_id,
                    "milestone_id": m1_id,
                    "title": "Bài 0: Biến Python",
                    "description": "Học biến Python",
                    "learning_objective": "Nắm biến Python",
                    "completion_criteria": "Pass quiz 1",
                    "covered_outcome_ids": ["M1-O1"],
                    "concept_ids": ["py-syntax-variables"],
                    "estimated_minutes": 60,  # scaled by beta=1.5 -> 90
                },
                {
                    "task_id": t1_id,
                    "milestone_id": m2_id,
                    "title": "Bài 1: Hàm & Vòng lặp (Protected)",
                    "description": "Bài thực hành hàm bảo vệ",
                    "learning_objective": "Thành thạo hàm",
                    "completion_criteria": "Pass 3 bài tập hàm",
                    "covered_outcome_ids": ["M2-O1"],
                    "concept_ids": ["py-control-flow-functions"],
                    "estimated_minutes": 60,  # scaled by beta=1.5 -> 90 (2 blocks: 60+30)
                },
                {
                    "task_id": t2_id,
                    "milestone_id": m2_id,
                    "title": "Bài 2: Unit Test Hàm (Sẽ quá hạn)",
                    "description": "Viết unit test hàm",
                    "learning_objective": "Viết pytest cho hàm",
                    "completion_criteria": "Pass pytest",
                    "covered_outcome_ids": ["M2-O2"],
                    "concept_ids": ["py-control-flow-functions"],
                    "estimated_minutes": 60,  # scaled by beta=1.5 -> 90
                },
                {
                    "task_id": t3_id,
                    "milestone_id": m2_id,
                    "title": "Bài 3: Ôn tập tổng hợp (Tương lai)",
                    "description": "Ôn tập giữ nguyên lịch",
                    "learning_objective": "Củng cố kiến thức",
                    "completion_criteria": "Hoàn thành đề ôn",
                    "covered_outcome_ids": ["M2-O2"],
                    "concept_ids": ["py-control-flow-functions"],
                    "estimated_minutes": 60,  # scaled by beta=1.5 -> 90
                },
            ],
            "dependencies": [
                {"predecessor_id": t0_id, "successor_id": t1_id, "is_mandatory": True},
                {"predecessor_id": t1_id, "successor_id": t2_id, "is_mandatory": True},
            ],
        }
        app.dependency_overrides[get_llm_provider] = lambda: StubLLMAdapter(
            canned_responses=[canned_tasks]
        )
        prop_job = await client.post(f"/api/v1/roadmaps/{roadmap_id}/proposals/generate-jobs")
        assert prop_job.status_code == 202
        prop_sse = await client.get(prop_job.json()["stream_url"])
        assert "event: completed" in prop_sse.text, prop_sse.text

        curr_prop = (await client.get(f"/api/v1/roadmaps/{roadmap_id}/proposals/current")).json()
        apply_init = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{curr_prop['id']}/apply",
            json={"confirm_warnings": True, "confirm_partial_schedule": True},
        )
        assert apply_init.status_code == 200, apply_init.text

        # 3. Mutate DB to simulate real execution state:
        #    - T0 -> COMPLETED
        #    - T1 -> multi-block is_protected=True (ensure at least 1 protected block, and if multi-block preserve all)
        #    - T2 -> overdue (past scheduled_date) + StudySessionORM + session_tasks row (forces UUID rotation on Apply!)
        #    - T3 -> keep in future (>= today_vn + 7 days)
        past_mon = today_vn - timedelta(days=(today_vn.weekday() - 0) % 7 or 7)
        if past_mon >= today_vn:
            past_mon -= timedelta(days=7)
        # Find next valid Mon/Wed/Fri >= today_vn + 7 for T3
        future_day = today_vn + timedelta(days=10)
        while future_day.weekday() not in (0, 2, 4):
            future_day += timedelta(days=1)

        async with async_session_factory() as session:
            t0_orm = await session.get(TaskORM, UUID(t0_id))
            t1_orm = await session.get(TaskORM, UUID(t1_id))
            t2_orm = await session.get(TaskORM, UUID(t2_id))
            t3_orm = await session.get(TaskORM, UUID(t3_id))
            assert t0_orm and t1_orm and t2_orm and t3_orm

            t0_orm.status = "COMPLETED"
            t0_orm.completed_at = datetime.now(UTC)

            # Mark T1 blocks as protected (split T1 across 2 blocks if not already split to exercise multi-block!)
            t1_blocks = list(
                (
                    await session.execute(
                        select(ScheduleBlockORM)
                        .where(ScheduleBlockORM.task_id == UUID(t1_id))
                        .order_by(ScheduleBlockORM.sequence_in_task.asc())
                    )
                )
                .scalars()
                .all()
            )
            assert len(t1_blocks) >= 1
            if len(t1_blocks) == 1:
                # Split into 60m + 30m protected blocks on same day or slot to exercise multi-block preservation
                orig = t1_blocks[0]
                mid_time = orig.start_time + timedelta(minutes=60)
                orig.end_time = mid_time
                orig.scheduled_duration_minutes = 60
                orig.is_protected = True
                second = ScheduleBlockORM(
                    id=uuid7(),
                    roadmap_id=orig.roadmap_id,
                    official_schedule_id=orig.official_schedule_id,
                    task_id=orig.task_id,
                    sequence_in_task=2,
                    block_type=orig.block_type,
                    block_date=orig.block_date,
                    start_time=mid_time,
                    end_time=mid_time + timedelta(minutes=30),
                    scheduled_duration_minutes=30,
                    is_protected=True,
                    status="PLANNED",
                    sync_status=orig.sync_status,
                )
                session.add(second)
                t1_orm.scheduled_start = orig.start_time
                t1_orm.scheduled_end = second.end_time
            else:
                for b in t1_blocks:
                    b.is_protected = True

            # Set T2 overdue in the past AND attach session_tasks history (ON DELETE RESTRICT)
            t2_orm.scheduled_date = past_mon
            t2_orm.scheduled_start = datetime(
                past_mon.year, past_mon.month, past_mon.day, 12, 0, tzinfo=UTC
            )
            t2_orm.scheduled_end = datetime(
                past_mon.year, past_mon.month, past_mon.day, 13, 30, tzinfo=UTC
            )
            t2_orm.learning_resources_json = [
                {
                    "resource_id": "res-py-ctrl",
                    "title": "Python Control Flow Docs",
                    "url": "https://docs.python.org/3/tutorial/controlflow.html",
                    "type": "DOCS",
                }
            ]

            study_sess = StudySessionORM(
                id=uuid7(),
                user_id=user_id,
                roadmap_id=roadmap_id,
                started_at=datetime.now(UTC) - timedelta(days=3),
                ended_at=datetime.now(UTC) - timedelta(days=3) + timedelta(minutes=25),
                planned_minutes=90,
                actual_minutes=25,
                status="PARTIAL_COMPLETED",
                last_heartbeat_at=datetime.now(UTC) - timedelta(days=3),
            )
            session.add(study_sess)
            await session.flush()
            await session.execute(
                text(
                    "INSERT INTO session_tasks (id, session_id, task_id, allocated_minutes, actual_minutes, status_after_session) "
                    "VALUES (:id, :sid, :tid, 90, 25, 'IN_PROGRESS')"
                ),
                {"id": uuid7(), "sid": study_sess.id, "tid": UUID(t2_id)},
            )

            # Set T3 cleanly on a future day
            t3_orm.scheduled_date = future_day
            t3_orm.scheduled_start = datetime(
                future_day.year, future_day.month, future_day.day, 12, 0, tzinfo=UTC
            )
            t3_orm.scheduled_end = datetime(
                future_day.year, future_day.month, future_day.day, 13, 30, tzinfo=UTC
            )
            t3_blocks = list(
                (
                    await session.execute(
                        select(ScheduleBlockORM).where(ScheduleBlockORM.task_id == UUID(t3_id))
                    )
                )
                .scalars()
                .all()
            )
            for idx_b, b in enumerate(t3_blocks):
                if idx_b == 0:
                    b.block_date = future_day
                    b.start_time = t3_orm.scheduled_start
                    b.end_time = t3_orm.scheduled_end
                    b.scheduled_duration_minutes = 90
                else:
                    b.status = "CANCELLED"

            await session.commit()

            t3_expected_date = future_day.isoformat()
            t3_expected_start = t3_orm.scheduled_start
            t1_expected_start = t1_orm.scheduled_start
            t1_expected_end = t1_orm.scheduled_end

        # 4. Run InitiateOverdueRecoveryUseCase (`POST /overdue-revise-jobs`)
        rec_job = await client.post(f"/api/v1/roadmaps/{roadmap_id}/overdue-revise-jobs")
        assert rec_job.status_code == 202, rec_job.text
        rec_sse = await client.get(rec_job.json()["stream_url"])
        assert "event: completed" in rec_sse.text, rec_sse.text

        rec_prop = (await client.get(f"/api/v1/roadmaps/{roadmap_id}/proposals/current")).json()
        rec_tasks = {t["task_id"]: t for t in rec_prop["tasks"]}
        assert t0_id not in rec_tasks  # COMPLETED never recreated
        assert all(t["estimated_minutes"] == 90 for t in rec_tasks.values())  # No beta^2 scaling!
        assert rec_tasks[t3_id]["scheduled_date"] == t3_expected_date
        assert datetime.fromisoformat(rec_tasks[t3_id]["scheduled_start"]) == t3_expected_start
        assert datetime.fromisoformat(rec_tasks[t1_id]["scheduled_start"]) == t1_expected_start
        assert datetime.fromisoformat(rec_tasks[t1_id]["scheduled_end"]) == t1_expected_end

        # 5. Apply overdue recovery proposal against real PostgreSQL!
        apply_rec = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{rec_prop['id']}/apply",
            json={"confirm_warnings": True, "confirm_partial_schedule": True},
        )
        assert apply_rec.status_code == 200, apply_rec.text

        # Verify PostgreSQL state after UUID rotation + protected preservation + COMPLETED preservation
        async with async_session_factory() as session:
            db_tasks = list(
                (await session.execute(select(TaskORM).where(TaskORM.roadmap_id == roadmap_id)))
                .scalars()
                .all()
            )
            active_tasks = [t for t in db_tasks if t.status != "CANCELLED"]
            completed_db = [t for t in active_tasks if t.status == "COMPLETED"]
            assert [t.id for t in completed_db] == [UUID(t0_id)]

            # T2 had session_tasks -> rotated to new UUID, old T2 CANCELLED
            old_t2 = await session.get(TaskORM, UUID(t2_id))
            assert old_t2 is not None and old_t2.status == "CANCELLED"
            new_t2 = next(t for t in active_tasks if t.title == "Bài 2: Unit Test Hàm (Sẽ quá hạn)")
            assert new_t2.id != UUID(t2_id)
            assert new_t2.estimated_minutes == 90
            assert new_t2.concept_id == "py-control-flow-functions"
            assert len(new_t2.learning_resources_json) == 1
            assert new_t2.learning_resources_json[0]["resource_id"] == "res-py-ctrl"
            assert new_t2.scheduled_date is not None and new_t2.scheduled_date >= today_vn

            # Dependencies MUST survive UUID rotation in TaskDependencyORM!
            db_deps = list(
                (
                    await session.execute(
                        select(TaskDependencyORM).where(TaskDependencyORM.roadmap_id == roadmap_id)
                    )
                )
                .scalars()
                .all()
            )
            dep_pairs = {(d.predecessor_id, d.successor_id) for d in db_deps}
            assert (UUID(t0_id), UUID(t1_id)) in dep_pairs
            assert (UUID(t1_id), new_t2.id) in dep_pairs

            # Protected blocks of T1 remain untouched & PLANNED & is_protected=True
            db_t1_blocks = list(
                (
                    await session.execute(
                        select(ScheduleBlockORM).where(
                            ScheduleBlockORM.task_id == UUID(t1_id),
                            ScheduleBlockORM.status == "PLANNED",
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(db_t1_blocks) == 2
            assert all(b.is_protected for b in db_t1_blocks)

        # 6. Also run ReoptimizeScheduleProposalUseCase (`POST /reoptimize-schedule`) -> `POST /apply`
        reopt_res = await client.post(f"/api/v1/roadmaps/{roadmap_id}/reoptimize-schedule")
        assert reopt_res.status_code == 201, reopt_res.text
        reopt_id = reopt_res.json()["id"]
        apply_reopt = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{reopt_id}/apply",
            json={"confirm_warnings": True, "confirm_partial_schedule": True},
        )
        assert apply_reopt.status_code == 200, apply_reopt.text
