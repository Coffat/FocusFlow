from datetime import UTC, date, datetime, timedelta

import pytest
from uuid6 import uuid7

from src.execution.domain.events.session_events import (
    StudySessionAbandonedEvent,
    StudySessionCompletedEvent,
)
from src.execution.domain.exceptions.execution_exceptions import (
    ExecutionDomainError,
    InvalidSessionStateError,
    InvalidTaskDurationError,
    InvalidTaskStateError,
    TakeawayValidationFailedError,
    TaskStalledInterventionRequiredError,
)
from src.execution.domain.models.study_session import (
    STICKY_NOTE_ENVELOPE_PREFIX,
    STUDIO_CONFIG_SENTINEL_PREFIX,
    DailyCheckin,
    SessionMode,
    SessionStatus,
    StickyNotePayload,
    StudioConfigPayload,
    StudySession,
    TimeSufficiency,
    decode_sticky_note_content,
    decode_studio_config,
    encode_sticky_note_content,
    encode_studio_config,
)
from src.execution.domain.models.task import Task, TaskDependency, TaskStatus
from src.execution.domain.services.backlog_priority_ranker import BacklogPriorityRanker
from src.execution.domain.services.takeaway_guard import TakeawayGuard


class TestTakeawayGuard:
    def test_rejects_short_takeaway(self) -> None:
        with pytest.raises(TakeawayValidationFailedError) as exc_info:
            TakeawayGuard.validate("Too short note here", task_title="Asyncio basics")
        assert exc_info.value.code == "TAKEAWAY_VALIDATION_FAILED"

    def test_rejects_fewer_than_6_distinct_words(self) -> None:
        with pytest.raises(TakeawayValidationFailedError):
            TakeawayGuard.validate("ok ok ok ok ok ok ok ok ok ok ok", task_title="Topic")

    def test_rejects_more_than_5_consecutive_same_char(self) -> None:
        with pytest.raises(TakeawayValidationFailedError):
            TakeawayGuard.validate(
                "Hôm nay mình học về python aaaaaa và hiểu rõ hơn về coroutine",
                task_title="Python Coroutines",
            )

    def test_rejects_low_diversity_gibberish(self) -> None:
        with pytest.raises(TakeawayValidationFailedError):
            TakeawayGuard.validate(
                "asdf asdf asdf asdf asdf asdf asdf asdf",
                task_title="SQL Indexing",
            )
        with pytest.raises(TakeawayValidationFailedError):
            TakeawayGuard.validate(
                "123456 789012 345678 901234 567890 111222",
                task_title="SQL Indexing",
            )

    def test_rejects_copy_paste_of_task_title_and_description(self) -> None:
        title = "Thiết kế hệ thống hàng đợi bất đồng bộ với Redis Streams"
        desc = "Xây dựng worker consumer group và cơ chế ack đảm bảo không mất thông điệp"
        copied = f"{title} {desc}"
        with pytest.raises(TakeawayValidationFailedError):
            TakeawayGuard.validate(copied, task_title=title, task_description=desc)

    def test_accepts_genuine_vietnamese_and_english_reflection(self) -> None:
        res = TakeawayGuard.validate(
            "Mình đã hiểu cách Taskiq dùng Redis Streams XREADGROUP để phân phối tác vụ và tránh xử lý trùng.",
            task_title="Thiết kế hệ thống hàng đợi bất đồng bộ",
            task_description="Tìm hiểu worker",
        )
        assert res.is_valid is True
        assert res.distinct_word_count >= 6
        assert res.token_overlap_ratio < 0.85


class TestBacklogPriorityRanker:
    def test_4_tier_deterministic_ranking(self) -> None:
        now = datetime(2026, 11, 18, 8, 0, tzinfo=UTC)
        m1 = uuid7()
        m2 = uuid7()
        rm = uuid7()

        # t_high_deg: out_degree=2, ms=2, resched=0, mins=120
        t_high_deg = Task(
            id=uuid7(),
            roadmap_id=rm,
            milestone_id=m2,
            title="High Out Degree",
            estimated_minutes=120,
            reschedule_count=0,
            created_at=now,
            updated_at=now,
        )
        # t_ms1_resched: out_degree=1, ms=1, resched=2, mins=60
        t_ms1_resched = Task(
            id=uuid7(),
            roadmap_id=rm,
            milestone_id=m1,
            title="Milestone 1 High Reschedule",
            estimated_minutes=60,
            reschedule_count=2,
            created_at=now,
            updated_at=now,
        )
        # t_ms1_quick: out_degree=1, ms=1, resched=1, mins=20
        t_ms1_quick = Task(
            id=uuid7(),
            roadmap_id=rm,
            milestone_id=m1,
            title="Milestone 1 Quick",
            estimated_minutes=20,
            reschedule_count=1,
            created_at=now,
            updated_at=now,
        )
        # t_ms1_long: out_degree=1, ms=1, resched=1, mins=45
        t_ms1_long = Task(
            id=uuid7(),
            roadmap_id=rm,
            milestone_id=m1,
            title="Milestone 1 Long",
            estimated_minutes=45,
            reschedule_count=1,
            created_at=now,
            updated_at=now,
        )
        succ1 = Task(
            id=uuid7(),
            roadmap_id=rm,
            milestone_id=m2,
            title="Succ 1",
            estimated_minutes=30,
            created_at=now,
            updated_at=now,
        )
        succ2 = Task(
            id=uuid7(),
            roadmap_id=rm,
            milestone_id=m2,
            title="Succ 2",
            estimated_minutes=30,
            created_at=now,
            updated_at=now,
        )
        cancelled_succ = Task(
            id=uuid7(),
            roadmap_id=rm,
            milestone_id=m2,
            title="Cancelled Succ",
            estimated_minutes=30,
            status=TaskStatus.CANCELLED,
            created_at=now,
            updated_at=now,
        )

        deps = [
            TaskDependency(predecessor_id=t_high_deg.id, successor_id=succ1.id, roadmap_id=rm),
            TaskDependency(predecessor_id=t_high_deg.id, successor_id=succ2.id, roadmap_id=rm),
            TaskDependency(predecessor_id=t_ms1_resched.id, successor_id=succ1.id, roadmap_id=rm),
            TaskDependency(predecessor_id=t_ms1_quick.id, successor_id=succ1.id, roadmap_id=rm),
            TaskDependency(predecessor_id=t_ms1_long.id, successor_id=succ1.id, roadmap_id=rm),
            # Cancelled successor must not count toward out_degree
            TaskDependency(
                predecessor_id=t_ms1_long.id, successor_id=cancelled_succ.id, roadmap_id=rm
            ),
        ]
        statuses = {
            t.id: t.status
            for t in (
                t_high_deg,
                t_ms1_resched,
                t_ms1_quick,
                t_ms1_long,
                succ1,
                succ2,
                cancelled_succ,
            )
        }
        ranked = BacklogPriorityRanker.rank(
            [t_ms1_long, t_ms1_quick, t_high_deg, t_ms1_resched],
            dependencies=deps,
            milestone_sequences={m1: 1, m2: 2},
            active_task_statuses=statuses,
        )
        assert [r.task.id for r in ranked] == [
            t_high_deg.id,
            t_ms1_resched.id,
            t_ms1_quick.id,
            t_ms1_long.id,
        ]
        assert [r.priority_rank for r in ranked] == [1, 2, 3, 4]
        assert ranked[0].out_degree == 2
        assert ranked[3].out_degree == 1


class TestTaskDomain:
    def test_duration_bounds_and_derived_flags(self) -> None:
        now = datetime(2026, 11, 18, 8, 0, tzinfo=UTC)
        with pytest.raises(InvalidTaskDurationError):
            Task(title="Too short", estimated_minutes=14, created_at=now, updated_at=now)
        with pytest.raises(InvalidTaskDurationError):
            Task(title="Too long", estimated_minutes=241, created_at=now, updated_at=now)

        task = Task(
            title="Valid task",
            estimated_minutes=45,
            scheduled_date=date(2026, 11, 17),
            reschedule_count=3,
            created_at=now,
            updated_at=now,
        )
        assert task.is_overdue(date(2026, 11, 18)) is True
        assert task.is_overdue(date(2026, 11, 17)) is False
        assert task.is_stalled() is True

        with pytest.raises(TaskStalledInterventionRequiredError):
            task.reschedule(
                scheduled_date=date(2026, 11, 20),
                scheduled_start=None,
                scheduled_end=None,
                today=date(2026, 11, 18),
                now=now,
            )

        # Explicit stalled commitment resets reschedule_count to 0
        counted = task.reschedule(
            scheduled_date=date(2026, 11, 20),
            scheduled_start=None,
            scheduled_end=None,
            today=date(2026, 11, 18),
            now=now,
            allow_stalled_commitment=True,
        )
        assert counted is False
        assert task.reschedule_count == 0
        assert task.is_stalled() is False

    def test_complete_reopen_and_cancel_transitions(self) -> None:
        now = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
        task = Task(
            title="Learn Postgres Locks",
            estimated_minutes=30,
            scheduled_date=date(2026, 11, 18),
            reschedule_count=2,
            created_at=now,
            updated_at=now,
        )
        task.complete(now)
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at == now
        assert task.reschedule_count == 0

        with pytest.raises(InvalidTaskStateError):
            task.cancel(now)

        task.reopen(now)
        assert task.status == TaskStatus.TODO
        assert task.completed_at is None

        task.cancel(now)
        assert task.status == TaskStatus.CANCELLED
        assert task.scheduled_date is None


class TestStudySessionDomainOS01:
    def test_heartbeat_monotonic_and_finalize_completed_emits_event(self) -> None:
        t0 = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
        session = StudySession(
            user_id=uuid7(),
            roadmap_id=uuid7(),
            started_at=t0,
            planned_minutes=50,
            last_heartbeat_at=t0,
            session_mode=SessionMode.STANDARD,
            created_at=t0,
            updated_at=t0,
        )
        session.record_heartbeat(now=t0 + timedelta(minutes=20), actual_minutes=20)
        session.record_heartbeat(now=t0 + timedelta(minutes=25), actual_minutes=10)
        assert session.actual_minutes == 20  # monotonic

        status = session.finalize(
            now=t0 + timedelta(minutes=50),
            early_stop=False,
            has_completed_task=True,
            has_valid_takeaway=True,
            checkin=DailyCheckin(
                time_sufficiency=TimeSufficiency.JUST_RIGHT,
                perceived_difficulty=3,
                focus_level=5,
            ),
        )
        assert status == SessionStatus.COMPLETED
        events = session.pull_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], StudySessionCompletedEvent)
        assert events[0].actual_duration_seconds == 50 * 60

        with pytest.raises(InvalidSessionStateError):
            session.record_heartbeat(now=t0 + timedelta(minutes=55))

    def test_os01_early_stop_standard_and_mvs(self) -> None:
        t0 = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)

        # Standard < 50% without completed task -> CANCELLED + AbandonedEvent
        s_cancel = StudySession(
            user_id=uuid7(),
            roadmap_id=uuid7(),
            started_at=t0,
            planned_minutes=60,
            last_heartbeat_at=t0,
            session_mode=SessionMode.STANDARD,
            created_at=t0,
            updated_at=t0,
        )
        st1 = s_cancel.finalize(
            now=t0 + timedelta(minutes=20),
            early_stop=True,
            has_completed_task=False,
            has_valid_takeaway=True,
        )
        assert st1 == SessionStatus.CANCELLED
        assert isinstance(s_cancel.pull_domain_events()[0], StudySessionAbandonedEvent)

        # Standard >= 50% -> PARTIAL_COMPLETED + CompletedEvent
        s_partial = StudySession(
            user_id=uuid7(),
            roadmap_id=uuid7(),
            started_at=t0,
            planned_minutes=60,
            last_heartbeat_at=t0,
            session_mode=SessionMode.STANDARD,
            created_at=t0,
            updated_at=t0,
        )
        st2 = s_partial.finalize(
            now=t0 + timedelta(minutes=30),
            early_stop=True,
            has_completed_task=False,
            has_valid_takeaway=False,
        )
        assert st2 == SessionStatus.PARTIAL_COMPLETED
        assert isinstance(s_partial.pull_domain_events()[0], StudySessionCompletedEvent)

        # MVS >= 10m WITHOUT valid takeaway -> CANCELLED
        s_mvs_no_takeaway = StudySession(
            user_id=uuid7(),
            roadmap_id=uuid7(),
            started_at=t0,
            planned_minutes=15,
            last_heartbeat_at=t0,
            session_mode=SessionMode.MVS,
            created_at=t0,
            updated_at=t0,
        )
        assert (
            s_mvs_no_takeaway.finalize(
                now=t0 + timedelta(minutes=12),
                early_stop=True,
                has_completed_task=False,
                has_valid_takeaway=False,
            )
            == SessionStatus.CANCELLED
        )

        # MVS >= 10m WITH valid takeaway -> PARTIAL_COMPLETED
        s_mvs_ok = StudySession(
            user_id=uuid7(),
            roadmap_id=uuid7(),
            started_at=t0,
            planned_minutes=15,
            last_heartbeat_at=t0,
            session_mode=SessionMode.MVS,
            created_at=t0,
            updated_at=t0,
        )
        assert (
            s_mvs_ok.finalize(
                now=t0 + timedelta(minutes=10),
                early_stop=True,
                has_completed_task=False,
                has_valid_takeaway=True,
            )
            == SessionStatus.PARTIAL_COMPLETED
        )

    def test_resolve_pending_takeaway_promotes_qualifying_cancelled_sessions(self) -> None:
        t0 = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)

        # Qualifying MVS (>= 10 min) cancelled due to missing takeaway -> PARTIAL_COMPLETED
        s_mvs = StudySession(
            user_id=uuid7(),
            roadmap_id=uuid7(),
            started_at=t0,
            ended_at=t0 + timedelta(minutes=10),
            planned_minutes=15,
            actual_minutes=10,
            status=SessionStatus.CANCELLED,
            last_heartbeat_at=t0 + timedelta(minutes=10),
            session_mode=SessionMode.MVS,
            pending_takeaway=True,
            created_at=t0,
            updated_at=t0,
        )
        s_mvs.resolve_pending_takeaway(now=t0 + timedelta(minutes=20))
        assert s_mvs.pending_takeaway is False
        assert s_mvs.status == SessionStatus.PARTIAL_COMPLETED

        # Qualifying STANDARD (>= 50% planned) -> PARTIAL_COMPLETED
        s_std = StudySession(
            user_id=uuid7(),
            roadmap_id=uuid7(),
            started_at=t0,
            ended_at=t0 + timedelta(minutes=30),
            planned_minutes=60,
            actual_minutes=30,
            status=SessionStatus.CANCELLED,
            last_heartbeat_at=t0 + timedelta(minutes=30),
            session_mode=SessionMode.STANDARD,
            pending_takeaway=True,
            created_at=t0,
            updated_at=t0,
        )
        s_std.resolve_pending_takeaway(now=t0 + timedelta(minutes=35))
        assert s_std.pending_takeaway is False
        assert s_std.status == SessionStatus.PARTIAL_COMPLETED

        # Non-qualifying STANDARD (< 50%) stays CANCELLED
        s_short = StudySession(
            user_id=uuid7(),
            roadmap_id=uuid7(),
            started_at=t0,
            ended_at=t0 + timedelta(minutes=10),
            planned_minutes=60,
            actual_minutes=10,
            status=SessionStatus.CANCELLED,
            last_heartbeat_at=t0 + timedelta(minutes=10),
            session_mode=SessionMode.STANDARD,
            pending_takeaway=True,
            created_at=t0,
            updated_at=t0,
        )
        s_short.resolve_pending_takeaway(now=t0 + timedelta(minutes=15))
        assert s_short.pending_takeaway is False
        assert s_short.status == SessionStatus.CANCELLED


class TestStickyNotesAndStudioConfigCodecs:
    def test_sticky_note_envelope_round_trip_and_legacy_fallback(self) -> None:
        payload = StickyNotePayload(
            title="Ghi chú Postgres",
            body="Nhớ dùng FOR UPDATE SKIP LOCKED cho sweeper.",
            color="sage",
            pinned=True,
            pos_x=120.5,
            pos_y=84.0,
            z_index=3,
            origin_session_id="sess-123",
        )
        encoded = encode_sticky_note_content(payload)
        assert encoded.startswith(STICKY_NOTE_ENVELOPE_PREFIX)

        decoded = decode_sticky_note_content(encoded)
        assert decoded == payload

        # Plain legacy note without prefix
        legacy = decode_sticky_note_content("Plain legacy study note")
        assert legacy == StickyNotePayload(
            title="",
            body="Plain legacy study note",
            color="cream",
            pinned=True,
        )

    def test_sticky_note_validation_errors(self) -> None:
        with pytest.raises(ExecutionDomainError) as exc_color:
            encode_sticky_note_content(StickyNotePayload(title="T", body="B", color="neon"))
        assert exc_color.value.code == "INVALID_STICKY_NOTE_COLOR"

        with pytest.raises(ExecutionDomainError) as exc_title:
            encode_sticky_note_content(StickyNotePayload(title="x" * 201, body="B"))
        assert exc_title.value.code == "INVALID_STICKY_NOTE_TITLE"

        with pytest.raises(ExecutionDomainError) as exc_body:
            encode_sticky_note_content(StickyNotePayload(title="T", body="y" * 5001))
        assert exc_body.value.code == "INVALID_STICKY_NOTE_BODY"

    def test_studio_config_codec_round_trip_and_validation(self) -> None:
        cfg = StudioConfigPayload(
            scene="cafe",
            clock_style="flip",
            clock_size="md",
            show_seconds=False,
            show_in_tab_title=True,
            tab_guard_enabled=False,
            zen_lock_enabled=True,
            blocklist=("reddit.com", "x.com"),
            parking_lot=(
                {"id": "p1", "text": "Xem lại index B-tree", "created_at": "2026-11-18T10:00:00Z"},
            ),
        )
        encoded = encode_studio_config(cfg)
        assert encoded.startswith(STUDIO_CONFIG_SENTINEL_PREFIX)
        assert decode_studio_config(encoded) == cfg

        # Non-sentinel falls back to defaults
        assert decode_studio_config("not-a-config") == StudioConfigPayload()

        with pytest.raises(ExecutionDomainError) as exc_scene:
            encode_studio_config(StudioConfigPayload(scene="spaceship"))
        assert exc_scene.value.code == "INVALID_STUDIO_CONFIG"

        with pytest.raises(ExecutionDomainError) as exc_style:
            encode_studio_config(StudioConfigPayload(clock_style="sundial"))
        assert exc_style.value.code == "INVALID_STUDIO_CONFIG"

        with pytest.raises(ExecutionDomainError) as exc_size:
            encode_studio_config(StudioConfigPayload(clock_size="xl"))
        assert exc_size.value.code == "INVALID_STUDIO_CONFIG"
