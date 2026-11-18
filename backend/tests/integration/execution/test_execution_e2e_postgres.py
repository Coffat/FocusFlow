from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

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
from src.evaluation.application.dtos.intelligence import GenerateWeeklyReviewRequestDTO
from src.execution.infrastructure.orm.session_orm import (
    SessionTaskORM,
    StudyNoteORM,
    StudySessionORM,
)
from src.execution.infrastructure.orm.task_orm import TaskORM
from src.execution.presentation.tasks import sweep_abandoned_study_sessions
from src.main import app
from src.planning.infrastructure.orm.planning_orm import RoadmapORM, ScheduleBlockORM
from src.planning.presentation.deps import get_llm_provider
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM
from src.shared_kernel.infrastructure.sse import default_in_memory_sse_job_store
from tests.helpers.llm_stubs import StubLLMAdapter


async def _seed_user_with_mode_b(
    *,
    email_prefix: str,
    slots_days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6),
    slot_start: time = time(19, 0),
    slot_end: time = time(22, 0),
) -> UUID:
    user_id = uuid7()
    now = datetime.now(UTC)

    async with async_session_factory() as session:
        user = UserORM(
            id=user_id,
            email=f"{email_prefix}_{user_id.hex[:8]}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="PR-2 Execution Learner",
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
            opt_session_minutes=45,
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
                d: {"enabled": True, "quota_hours": 3.0}
                for d in (
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
        slots = [
            AvailabilitySlotORM(
                id=uuid7(),
                availability_id=avail_id,
                day_of_week=dow,
                slot_type="FIXED",
                start_time=slot_start,
                end_time=slot_end,
                end_day_offset=0,
                is_active=True,
            )
            for dow in slots_days
        ]
        session.add(user)
        await session.flush()
        session.add_all([quota, profile, avail])
        await session.flush()
        session.add_all(slots)
        await session.commit()
    return user_id


async def _cleanup_users(user_ids: list[UUID]) -> None:
    if not user_ids:
        return
    async with async_session_factory() as session:
        await session.execute(
            text(
                "DELETE FROM outbox_events WHERE aggregate_id IN ("
                "  SELECT id FROM study_sessions WHERE user_id = ANY(:uids)"
                ")"
            ),
            {"uids": user_ids},
        )
        await session.execute(
            text(
                "DELETE FROM session_tasks WHERE session_id IN "
                "(SELECT id FROM study_sessions WHERE user_id = ANY(:uids))"
            ),
            {"uids": user_ids},
        )
        await session.execute(
            delete(OutboxEventORM).where(OutboxEventORM.aggregate_id.in_(user_ids))
        )
        await session.execute(delete(UserORM).where(UserORM.id.in_(user_ids)))
        await session.commit()


@pytest.fixture
async def execution_users() -> AsyncGenerator[tuple[UUID, UUID], None]:
    default_in_memory_sse_job_store.clear()
    user_a = await _seed_user_with_mode_b(email_prefix="exec_a")
    user_b = await _seed_user_with_mode_b(email_prefix="exec_b")
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_learner_id] = lambda: user_a
    app.dependency_overrides[get_llm_provider] = lambda: StubLLMAdapter()
    try:
        yield user_a, user_b
    finally:
        app.dependency_overrides.clear()
        default_in_memory_sse_job_store.clear()
        await _cleanup_users([user_a, user_b])


@pytest.mark.asyncio
async def test_execution_full_lifecycle_analytics_idor_and_concurrency_postgres(
    execution_users: tuple[UUID, UUID],
) -> None:
    user_a, user_b = execution_users
    transport = ASGITransport(app=app)
    vn_tz = ZoneInfo("Asia/Ho_Chi_Minh")
    today_vn = datetime.now(UTC).astimezone(vn_tz).date()
    start_date = today_vn
    target_date = today_vn + timedelta(days=21)

    canned_milestones = {
        "milestones": [
            {
                "sequence_order": 1,
                "title": "Chặng 1: Nền tảng Execution",
                "description": "Học các khái niệm cốt lõi",
                "learning_outcomes": ["Hiểu vòng đời Task", "Thực hành Pomodoro"],
                "completion_criteria": "Hoàn thành bài 1 và bài 2",
                "estimated_effort_minutes": 120,
                "required_concepts": [],
                "unverified_concepts": [],
                "dependencies": [],
            }
        ],
        "scope_summary": "FULL_SCOPE",
        "deferred_scope": [],
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create roadmap + approve milestones + generate & apply schedule proposal
        create_res = await client.post(
            "/api/v1/roadmaps",
            json={
                "title": "PR-2 Execution Lifecycle E2E",
                "description": "Kiểm thử vòng đời task & session trên PostgreSQL",
                "start_date": start_date.isoformat(),
                "target_date": target_date.isoformat(),
            },
        )
        assert create_res.status_code == 201, create_res.text
        roadmap_id = UUID(create_res.json()["id"])

        app.dependency_overrides[get_llm_provider] = lambda: StubLLMAdapter(
            canned_responses=[canned_milestones]
        )
        ms_job = await client.post(f"/api/v1/roadmaps/{roadmap_id}/milestones/generate-jobs")
        assert ms_job.status_code == 202
        ms_sse = await client.get(ms_job.json()["stream_url"])
        assert "event: completed" in ms_sse.text

        approve_res = await client.post(f"/api/v1/roadmaps/{roadmap_id}/milestones/approve")
        assert approve_res.status_code == 200
        m1_id = approve_res.json()["milestones"][0]["id"]

        t1_id = str(uuid7())
        t2_id = str(uuid7())
        t3_id = str(uuid7())
        canned_tasks = {
            "tasks": [
                {
                    "task_id": t1_id,
                    "milestone_id": m1_id,
                    "title": "Bài 1: Khởi tạo phiên học",
                    "description": "Thực hành Pomodoro và ghi chú Scratchpad",
                    "learning_objective": "Khởi tạo phiên học",
                    "completion_criteria": "Hoàn thành phiên học",
                    "covered_outcome_ids": ["M1-O1"],
                    "concept_ids": [],
                    "estimated_minutes": 45,
                },
                {
                    "task_id": t2_id,
                    "milestone_id": m1_id,
                    "title": "Bài 2: Tổng kết Takeaway",
                    "description": "Đúc kết kiến thức sau buổi học",
                    "learning_objective": "Đúc kết kiến thức",
                    "completion_criteria": "Hoàn thành takeaway",
                    "covered_outcome_ids": ["M1-O2"],
                    "concept_ids": [],
                    "estimated_minutes": 45,
                },
                {
                    "task_id": t3_id,
                    "milestone_id": m1_id,
                    "title": "Bài 3: Ôn tập cuối tuần",
                    "description": "Củng cố lại toàn bộ bài tập",
                    "learning_objective": "Củng cố kiến thức",
                    "completion_criteria": "Hoàn thành ôn tập",
                    "covered_outcome_ids": ["M1-O1"],
                    "concept_ids": [],
                    "estimated_minutes": 45,
                },
            ],
            "dependencies": [
                {"predecessor_id": t1_id, "successor_id": t2_id, "is_mandatory": True}
            ],
        }
        app.dependency_overrides[get_llm_provider] = lambda: StubLLMAdapter(
            canned_responses=[canned_tasks]
        )
        prop_job = await client.post(f"/api/v1/roadmaps/{roadmap_id}/proposals/generate-jobs")
        assert prop_job.status_code == 202, prop_job.text
        prop_sse = await client.get(prop_job.json()["stream_url"])
        assert "event: completed" in prop_sse.text, prop_sse.text

        curr_prop = (await client.get(f"/api/v1/roadmaps/{roadmap_id}/proposals/current")).json()
        prop_id = curr_prop["id"]

        apply_res = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{prop_id}/apply",
            json={"confirm_warnings": True, "confirm_partial_schedule": True},
        )
        assert apply_res.status_code == 200, apply_res.text

        # 2. Check /api/v1/tasks, /schedule/week, /sessions/today-focus
        tasks_res = await client.get("/api/v1/tasks", params={"roadmap_id": str(roadmap_id)})
        assert tasks_res.status_code == 200
        tasks_list = tasks_res.json()
        assert len(tasks_list) == 3
        tasks_by_title = {t["title"]: t for t in tasks_list}
        t1_data = tasks_by_title["Bài 1: Khởi tạo phiên học"]
        real_t1_id = UUID(t1_data["id"])
        real_t2_id = UUID(tasks_by_title["Bài 2: Tổng kết Takeaway"]["id"])
        real_t3_id = UUID(tasks_by_title["Bài 3: Ôn tập cuối tuần"]["id"])
        assert tasks_by_title["Bài 2: Tổng kết Takeaway"]["is_blocked"] is True
        assert t1_data["is_blocked"] is False

        week_res = await client.get(
            "/api/v1/tasks/schedule/week",
            params={"week_start": (today_vn - timedelta(days=today_vn.weekday())).isoformat()},
        )
        assert week_res.status_code == 200
        assert len(week_res.json()["items"]) >= 1

        focus_res = await client.get("/api/v1/sessions/today-focus")
        assert focus_res.status_code == 200
        if t1_data["scheduled_date"] == today_vn.isoformat():
            assert focus_res.json()["focus_task"]["id"] == str(real_t1_id)

        # Blocked task cannot be completed or started
        blocked_complete = await client.post(f"/api/v1/tasks/{real_t2_id}/complete")
        assert blocked_complete.status_code == 409
        assert blocked_complete.json()["code"] == "TASK_BLOCKED"

        blocked_start = await client.post(
            "/api/v1/sessions/start",
            json={"task_ids": [str(real_t2_id)], "session_mode": "STANDARD"},
        )
        assert blocked_start.status_code == 409
        assert blocked_start.json()["code"] == "TASK_BLOCKED"

        # 3. Manual task creation bounds + slot conflict + valid creation
        bad_dur = await client.post(
            "/api/v1/tasks",
            json={
                "roadmap_id": str(roadmap_id),
                "milestone_id": m1_id,
                "title": "Invalid short task",
                "estimated_minutes": 10,
            },
        )
        assert bad_dur.status_code == 422
        assert bad_dur.json()["code"] == "INVALID_TASK_DURATION"

        conflict_slot = await client.post(
            "/api/v1/tasks",
            json={
                "roadmap_id": str(roadmap_id),
                "milestone_id": m1_id,
                "title": "Conflicting Task",
                "estimated_minutes": 45,
                "scheduled_date": t1_data["scheduled_date"],
                "scheduled_start": t1_data["scheduled_start"],
                "scheduled_end": t1_data["scheduled_end"],
            },
        )
        assert conflict_slot.status_code == 409
        assert conflict_slot.json()["code"] == "SCHEDULE_SLOT_CONFLICT"

        manual_day = today_vn + timedelta(days=5)
        manual_start = datetime.combine(manual_day, time(20, 0), tzinfo=vn_tz)
        manual_end = datetime.combine(manual_day, time(20, 30), tzinfo=vn_tz)
        manual_ok = await client.post(
            "/api/v1/tasks",
            json={
                "roadmap_id": str(roadmap_id),
                "milestone_id": m1_id,
                "title": "Bài 4: Nhiệm vụ thủ công",
                "estimated_minutes": 30,
                "scheduled_date": manual_day.isoformat(),
                "scheduled_start": manual_start.isoformat(),
                "scheduled_end": manual_end.isoformat(),
            },
        )
        assert manual_ok.status_code == 201, manual_ok.text
        manual_task_id = UUID(manual_ok.json()["id"])

        patch_ok = await client.patch(
            f"/api/v1/tasks/{manual_task_id}",
            json={"title": "Bài 4: Nhiệm vụ thủ công đã sửa"},
        )
        assert patch_ok.status_code == 200
        assert patch_ok.json()["title"] == "Bài 4: Nhiệm vụ thủ công đã sửa"

        # Cancel manual task -> clears schedule_blocks
        del_ok = await client.delete(f"/api/v1/tasks/{manual_task_id}")
        assert del_ok.status_code == 200
        assert del_ok.json()["status"] == "CANCELLED"

        # Cycle detection on dependencies
        cycle_res = await client.post(
            f"/api/v1/tasks/{real_t1_id}/dependencies",
            json={"predecessor_id": str(real_t2_id), "is_mandatory": True},
        )
        assert cycle_res.status_code == 422
        assert cycle_res.json()["code"] == "DEPENDENCY_CYCLE_DETECTED"

        # 4. Concurrent POST /api/v1/sessions/start -> one 201, one 409
        start_r1, start_r2 = await asyncio.gather(
            client.post(
                "/api/v1/sessions/start",
                json={"task_ids": [str(real_t1_id)], "session_mode": "STANDARD"},
            ),
            client.post(
                "/api/v1/sessions/start",
                json={"task_ids": [str(real_t1_id)], "session_mode": "STANDARD"},
            ),
        )
        start_statuses = sorted([start_r1.status_code, start_r2.status_code])
        assert start_statuses == [201, 409], (start_r1.text, start_r2.text)
        active_sess_resp = start_r1 if start_r1.status_code == 201 else start_r2
        conflict_sess_resp = start_r2 if start_r1.status_code == 201 else start_r1
        assert conflict_sess_resp.json()["code"] == "ACTIVE_SESSION_EXISTS"
        session_id = UUID(active_sess_resp.json()["id"])

        # 5. Cross-user IDOR check -> User B gets 404 on User A's task & session
        app.dependency_overrides[get_current_learner_id] = lambda: user_b
        idor_task = await client.post(f"/api/v1/tasks/{real_t1_id}/complete")
        assert idor_task.status_code == 404
        idor_hb = await client.post(f"/api/v1/sessions/{session_id}/heartbeat", json={})
        assert idor_hb.status_code == 404
        idor_fin = await client.post(
            f"/api/v1/sessions/{session_id}/finalize",
            json={"takeaway": "Attempting cross-user finalize with enough characters here."},
        )
        assert idor_fin.status_code == 404

        # Switch back to User A
        app.dependency_overrides[get_current_learner_id] = lambda: user_a

        # 6. Heartbeat + Scratchpad
        hb_res = await client.post(
            f"/api/v1/sessions/{session_id}/heartbeat",
            json={
                "actual_minutes": 25,
                "scratchpad_content": "Ghi chú nháp về cách hoạt động của hàng đợi thực thi.",
            },
        )
        assert hb_res.status_code == 200, hb_res.text
        assert hb_res.json()["actual_minutes"] == 25
        assert "Ghi chú nháp" in hb_res.json()["scratchpad_content"]

        # TakeawayGuard rejects gibberish
        bad_fin = await client.post(
            f"/api/v1/sessions/{session_id}/finalize",
            json={"takeaway": "asdfasdf", "completed_task_ids": [str(real_t1_id)]},
        )
        assert bad_fin.status_code == 422
        assert bad_fin.json()["code"] == "TAKEAWAY_VALIDATION_FAILED"

        # 7. Concurrent POST /api/v1/sessions/{id}/finalize -> one 200, one 409
        fin_payload = {
            "early_stop": False,
            "completed_task_ids": [str(real_t1_id)],
            "takeaway": "Mình đã nắm được cách khởi tạo phiên học tập trung và lưu ghi chú nháp tự động.",
            "self_confidence": 5,
            "actual_minutes": 45,
            "checkin_time_sufficiency": "JUST_RIGHT",
            "checkin_perceived_difficulty": 3,
            "checkin_focus_level": 5,
        }
        fin_r1, fin_r2 = await asyncio.gather(
            client.post(f"/api/v1/sessions/{session_id}/finalize", json=fin_payload),
            client.post(f"/api/v1/sessions/{session_id}/finalize", json=fin_payload),
        )
        fin_statuses = sorted([fin_r1.status_code, fin_r2.status_code])
        assert fin_statuses == [200, 409], (fin_r1.text, fin_r2.text)
        ok_fin = fin_r1 if fin_r1.status_code == 200 else fin_r2
        err_fin = fin_r2 if fin_r1.status_code == 200 else fin_r1
        assert ok_fin.json()["status"] == "COMPLETED"
        assert ok_fin.json()["actual_minutes"] == 45
        assert err_fin.json()["code"] == "INVALID_SESSION_STATE"

        # Verify Postgres state: tasks, schedule_blocks, study_sessions, session_tasks, study_notes, outbox_events
        async with async_session_factory() as db:
            t1_row = (
                await db.execute(select(TaskORM).where(TaskORM.id == real_t1_id))
            ).scalar_one()
            assert t1_row.status == "COMPLETED"
            assert t1_row.completed_at is not None

            blk_rows = list(
                (
                    await db.execute(
                        select(ScheduleBlockORM).where(ScheduleBlockORM.task_id == real_t1_id)
                    )
                )
                .scalars()
                .all()
            )
            assert blk_rows and all(b.status == "COMPLETED" for b in blk_rows)

            sess_row = (
                await db.execute(select(StudySessionORM).where(StudySessionORM.id == session_id))
            ).scalar_one()
            assert sess_row.status == "COMPLETED"
            assert sess_row.checkin_time_sufficiency == "JUST_RIGHT"
            assert sess_row.checkin_focus_level == 5

            st_row = (
                await db.execute(
                    select(SessionTaskORM).where(
                        SessionTaskORM.session_id == session_id,
                        SessionTaskORM.task_id == real_t1_id,
                    )
                )
            ).scalar_one()
            assert st_row.status_after_session == "COMPLETED"

            notes = list(
                (
                    await db.execute(
                        select(StudyNoteORM).where(StudyNoteORM.session_id == session_id)
                    )
                )
                .scalars()
                .all()
            )
            assert {n.note_type for n in notes} == {"SCRATCHPAD", "TAKEAWAY"}

            outbox_rows = list(
                (
                    await db.execute(
                        select(OutboxEventORM).where(OutboxEventORM.aggregate_id == session_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(outbox_rows) == 1
            assert outbox_rows[0].event_type == "StudySessionCompletedEvent"

            # Also verify manual task block was cancelled
            manual_blks = list(
                (
                    await db.execute(
                        select(ScheduleBlockORM).where(ScheduleBlockORM.task_id == manual_task_id)
                    )
                )
                .scalars()
                .all()
            )
            assert manual_blks and all(b.status == "CANCELLED" for b in manual_blks)

        # 8. Analytics & Evaluation Dashboard & Weekly Review integration
        analytics_sum = await client.get("/api/v1/analytics/summary")
        assert analytics_sum.status_code == 200, analytics_sum.text
        a_data = analytics_sum.json()
        assert a_data["total_focused_hours"] == pytest.approx(0.75, abs=0.01)
        assert a_data["completed_tasks_count"] == 1
        assert a_data["total_tasks_count"] == 3
        assert a_data["task_completion_rate"] == pytest.approx(33.3, abs=0.2)
        assert a_data["active_streak_days"] >= 1
        assert len(a_data["daily_metrics"]) == 7

        analytics_wk = await client.get("/api/v1/analytics/weekly")
        assert analytics_wk.status_code == 200
        assert analytics_wk.json()["completed_sessions_count"] == 1
        assert len(analytics_wk.json()["daily_breakdown"]) == 7

        dash_res = await client.get("/api/v1/evaluation/dashboard-summary")
        assert dash_res.status_code == 200
        dash = dash_res.json()
        assert dash["kpi"]["monthly_hours"] >= 0.7
        assert dash["kpi"]["streak_days"] >= 1
        assert dash["active_roadmaps"][0]["completed_tasks"] == 1

        # GenerateWeeklyReviewUseCase reflects the completed session & task
        async with async_session_factory() as db:
            from src.account.public_api import (
                create_learner_memory_query_port,
            )
            from src.evaluation.application.use_cases.intelligence import (
                GenerateWeeklyReviewUseCase,
            )
            from src.evaluation.infrastructure.repositories.intelligence_repository import (
                SqlAlchemyEvaluationIntelligenceRepository,
            )
            from src.execution.public_api import create_weekly_execution_metrics_port
            from src.planning.public_api import create_milestone_ownership_port
            from src.shared_kernel.infrastructure.database.sqlalchemy_uow import (
                SqlAlchemyUnitOfWork,
            )
            from src.shared_kernel.infrastructure.workflow.repository import (
                SqlAlchemyWorkflowRepository,
            )

            review_llm = StubLLMAdapter(
                canned_responses=[
                    {
                        "strengths_feedback": "Bạn đã hoàn thành tốt 1 phiên học 45 phút trong tuần.",
                        "bottlenecks_feedback": "Cần tiếp tục các bài còn lại.",
                        "action_recommendations": "Duy trì lịch học buổi tối.",
                        "memory_updates": [],
                    }
                ]
            )
            review_uc = GenerateWeeklyReviewUseCase(
                repository=SqlAlchemyEvaluationIntelligenceRepository(db),
                ownership=create_milestone_ownership_port(db),
                uow=SqlAlchemyUnitOfWork(db),
                learner_memory_port=create_learner_memory_query_port(db),
                execution_metrics_port=create_weekly_execution_metrics_port(db),
                workflow_repo=SqlAlchemyWorkflowRepository(db),
                llm_provider=review_llm,
            )
            monday = today_vn - timedelta(days=today_vn.weekday())
            sunday = monday + timedelta(days=6)
            review_dto = await review_uc.execute(
                user_a,
                GenerateWeeklyReviewRequestDTO(
                    roadmap_id=roadmap_id,
                    period_start=monday,
                    period_end=sunday,
                    user_reflection={"energy": "good"},
                ),
            )
            assert review_dto.quantitative_summary["completed_sessions_count"] >= 1
            assert review_dto.quantitative_summary["completed_minutes"] >= 45

        # 9. Reopen & Reschedule & Move to Backlog + BacklogPriorityRanker
        reopen_res = await client.post(f"/api/v1/tasks/{real_t1_id}/reopen")
        assert reopen_res.status_code == 200
        assert reopen_res.json()["status"] == "TODO"

        async with async_session_factory() as db:
            b_reopened = (
                await db.execute(
                    select(ScheduleBlockORM).where(ScheduleBlockORM.task_id == real_t1_id)
                )
            ).scalar_one()
            assert b_reopened.status == "PLANNED"

        # Complete t1 again so t2 is unblocked, then test moving t3 to backlog
        re_comp = await client.post(f"/api/v1/tasks/{real_t1_id}/complete")
        assert re_comp.status_code == 200

        # Move t3 to backlog
        backlog_move = await client.post(
            f"/api/v1/tasks/{real_t3_id}/reschedule",
            json={"scheduled_date": None, "reason": "Đưa về backlog"},
        )
        assert backlog_move.status_code == 200
        assert backlog_move.json()["scheduled_date"] is None

        backlog_list = await client.get("/api/v1/tasks/backlog")
        assert backlog_list.status_code == 200
        assert any(item["id"] == str(real_t3_id) for item in backlog_list.json())

        # Schedule t3 back to day+3
        day3 = today_vn + timedelta(days=3)
        resched_ok = await client.post(
            f"/api/v1/tasks/{real_t3_id}/reschedule",
            json={
                "scheduled_date": day3.isoformat(),
                "scheduled_start": datetime.combine(day3, time(19, 0), tzinfo=vn_tz).isoformat(),
                "scheduled_end": datetime.combine(day3, time(19, 45), tzinfo=vn_tz).isoformat(),
                "reason": "Xếp lại từ backlog",
            },
        )
        assert resched_ok.status_code == 200
        assert resched_ok.json()["scheduled_date"] == day3.isoformat()

        # 10. Test STALLED guard & overdue reschedule budget
        async with async_session_factory() as db:
            t3_orm = (
                await db.execute(select(TaskORM).where(TaskORM.id == real_t3_id))
            ).scalar_one()
            t3_orm.reschedule_count = 3
            await db.commit()

        stalled_res = await client.post(
            f"/api/v1/tasks/{real_t3_id}/reschedule",
            json={
                "scheduled_date": day3.isoformat(),
                "scheduled_start": datetime.combine(day3, time(20, 0), tzinfo=vn_tz).isoformat(),
                "scheduled_end": datetime.combine(day3, time(20, 45), tzinfo=vn_tz).isoformat(),
            },
        )
        assert stalled_res.status_code == 409
        assert stalled_res.json()["code"] == "TASK_STALLED_INTERVENTION_REQUIRED"

        # 11. Test MVS early stop -> PARTIAL_COMPLETED + WRLS + incomplete task to backlog
        mvs_start = await client.post(
            "/api/v1/sessions/start",
            json={"task_ids": [str(real_t2_id)], "session_mode": "MVS", "planned_minutes": 10},
        )
        assert mvs_start.status_code == 201
        mvs_sid = UUID(mvs_start.json()["id"])

        mvs_fin = await client.post(
            f"/api/v1/sessions/{mvs_sid}/finalize",
            json={
                "early_stop": True,
                "completed_task_ids": [],
                "actual_minutes": 12,
                "takeaway": "Học nhanh chế độ MVS 12 phút và tóm tắt được ý chính về Takeaway.",
                "self_confidence": 4,
            },
        )
        assert mvs_fin.status_code == 200
        assert mvs_fin.json()["status"] == "PARTIAL_COMPLETED"

        analytics_after_mvs = await client.get("/api/v1/analytics/summary")
        assert analytics_after_mvs.status_code == 200
        assert analytics_after_mvs.json()["weekly_recovered_learning_sessions"] >= 1

        # 12. Test pending_takeaway debt & resolve-takeaway
        debt_sid = uuid7()
        async with async_session_factory() as db:
            now_utc = datetime.now(UTC)
            db.add(
                StudySessionORM(
                    id=debt_sid,
                    user_id=user_a,
                    roadmap_id=roadmap_id,
                    started_at=now_utc - timedelta(minutes=25),
                    ended_at=now_utc - timedelta(minutes=5),
                    planned_minutes=25,
                    actual_minutes=20,
                    status="PARTIAL_COMPLETED",
                    last_heartbeat_at=now_utc - timedelta(minutes=5),
                    session_mode="STANDARD",
                    pending_takeaway=True,
                )
            )
            await db.commit()

        blocked_by_debt = await client.post(
            "/api/v1/sessions/start",
            json={"task_ids": [str(real_t2_id)], "session_mode": "STANDARD"},
        )
        assert blocked_by_debt.status_code == 409
        assert blocked_by_debt.json()["code"] == "PENDING_TAKEAWAY_REQUIRED"

        resolved_res = await client.post(
            f"/api/v1/sessions/{debt_sid}/resolve-takeaway",
            json={
                "takeaway": "Đây là phần đúc kết bổ sung sau khi phiên học trước bị ngắt kết nối đột ngột.",
                "self_confidence": 4,
            },
        )
        assert resolved_res.status_code == 200
        assert resolved_res.json()["pending_takeaway"] is False

        # 13. Test sweep_abandoned_study_sessions against REAL Postgres with session_tasks.status_after_session
        stale_sid = uuid7()
        now_sweep = datetime.now(UTC)
        async with async_session_factory() as db:
            db.add(
                StudySessionORM(
                    id=stale_sid,
                    user_id=user_a,
                    roadmap_id=roadmap_id,
                    started_at=now_sweep - timedelta(minutes=20),
                    ended_at=None,
                    planned_minutes=60,
                    actual_minutes=5,  # < 50%, so ONLY SessionTaskORM.status_after_session='COMPLETED' makes it PARTIAL_COMPLETED
                    status="IN_PROGRESS",
                    last_heartbeat_at=now_sweep - timedelta(minutes=10),
                    session_mode="STANDARD",
                    pending_takeaway=False,
                )
            )
            await db.flush()
            db.add(
                SessionTaskORM(
                    id=uuid7(),
                    session_id=stale_sid,
                    task_id=real_t1_id,
                    allocated_minutes=45,
                    actual_minutes=5,
                    status_after_session="COMPLETED",
                )
            )
            await db.commit()

        swept_count = await sweep_abandoned_study_sessions(
            session_factory=async_session_factory,
            now=now_sweep,
        )
        assert swept_count >= 1

        async with async_session_factory() as db:
            swept_row = (
                await db.execute(select(StudySessionORM).where(StudySessionORM.id == stale_sid))
            ).scalar_one()
            assert swept_row.status == "PARTIAL_COMPLETED"
            assert swept_row.ended_at is not None

            swept_outbox = (
                await db.execute(
                    select(OutboxEventORM).where(OutboxEventORM.aggregate_id == stale_sid)
                )
            ).scalar_one_or_none()
            assert swept_outbox is not None
            assert swept_outbox.event_type == "StudySessionAbandonedEvent"

        # 14. Test non-cyclic add/delete dependency, overdue reschedule budget, and roadmap ACTIVE -> COMPLETED -> ROADMAP_READ_ONLY
        dep_add = await client.post(
            f"/api/v1/tasks/{real_t3_id}/dependencies",
            json={"predecessor_id": str(real_t2_id), "is_mandatory": False},
        )
        assert dep_add.status_code == 201
        dep_del = await client.delete(f"/api/v1/tasks/{real_t3_id}/dependencies/{real_t2_id}")
        assert dep_del.status_code == 204

        # Overdue reschedule budget deduction on t2
        async with async_session_factory() as db:
            t2_orm = (
                await db.execute(select(TaskORM).where(TaskORM.id == real_t2_id))
            ).scalar_one()
            t2_orm.scheduled_date = today_vn - timedelta(days=1)
            t2_orm.scheduled_start = None
            t2_orm.scheduled_end = None
            await db.commit()

        day4 = today_vn + timedelta(days=4)
        overdue_resched = await client.post(
            f"/api/v1/tasks/{real_t2_id}/reschedule",
            json={
                "scheduled_date": day4.isoformat(),
                "scheduled_start": datetime.combine(day4, time(19, 0), tzinfo=vn_tz).isoformat(),
                "scheduled_end": datetime.combine(day4, time(19, 45), tzinfo=vn_tz).isoformat(),
                "reason": "Dời bài trễ hạn",
            },
        )
        assert overdue_resched.status_code == 200
        assert overdue_resched.json()["reschedule_count"] == 1

        async with async_session_factory() as db:
            rm_row = (
                await db.execute(select(RoadmapORM).where(RoadmapORM.id == roadmap_id))
            ).scalar_one()
            assert rm_row.weekly_reschedule_used == 1

        # Complete remaining tasks t2 & t3 -> roadmap transitions ACTIVE -> COMPLETED -> ROADMAP_READ_ONLY
        comp_t2 = await client.post(f"/api/v1/tasks/{real_t2_id}/complete")
        assert comp_t2.status_code == 200
        comp_t3 = await client.post(f"/api/v1/tasks/{real_t3_id}/complete")
        assert comp_t3.status_code == 200

        async with async_session_factory() as db:
            rm_done = (
                await db.execute(select(RoadmapORM).where(RoadmapORM.id == roadmap_id))
            ).scalar_one()
            assert rm_done.status == "COMPLETED"

        ro_reopen = await client.post(f"/api/v1/tasks/{real_t3_id}/reopen")
        assert ro_reopen.status_code == 409
        assert ro_reopen.json()["code"] == "ROADMAP_READ_ONLY"
