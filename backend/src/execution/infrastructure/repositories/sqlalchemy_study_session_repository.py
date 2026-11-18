from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.execution.application.ports.study_session_repository_port import (
    StudySessionRepositoryPort,
)
from src.execution.domain.exceptions.execution_exceptions import ActiveSessionExistsError
from src.execution.domain.models.study_session import (
    AlignmentFlag,
    NoteType,
    SessionMode,
    SessionStatus,
    SessionTask,
    StudyNote,
    StudySession,
    TimeSufficiency,
    VerificationStatus,
)
from src.execution.infrastructure.orm.session_orm import (
    SessionTaskORM,
    StudyNoteORM,
    StudySessionORM,
)


def _ensure_utc(dt: datetime) -> datetime:
    if dt == datetime.min:
        return datetime.now(UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class SqlAlchemyStudySessionRepository(StudySessionRepositoryPort):
    """SQLAlchemy repository for StudySession, SessionTask, StudyNote (add/flush only)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: StudySessionORM) -> StudySession:
        return StudySession(
            id=row.id,
            user_id=row.user_id,
            roadmap_id=row.roadmap_id,
            started_at=row.started_at,
            ended_at=row.ended_at,
            planned_minutes=int(row.planned_minutes),
            actual_minutes=int(row.actual_minutes),
            status=SessionStatus(row.status),
            last_heartbeat_at=row.last_heartbeat_at,
            session_mode=SessionMode(row.session_mode),
            pending_takeaway=bool(row.pending_takeaway),
            checkin_time_sufficiency=(
                TimeSufficiency(row.checkin_time_sufficiency)
                if row.checkin_time_sufficiency
                else None
            ),
            checkin_perceived_difficulty=row.checkin_perceived_difficulty,
            checkin_focus_level=row.checkin_focus_level,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _st_to_domain(row: SessionTaskORM) -> SessionTask:
        return SessionTask(
            id=row.id,
            session_id=row.session_id,
            task_id=row.task_id,
            allocated_minutes=int(row.allocated_minutes),
            actual_minutes=int(row.actual_minutes),
            status_after_session=row.status_after_session,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _note_to_domain(row: StudyNoteORM) -> StudyNote:
        return StudyNote(
            id=row.id,
            user_id=row.user_id,
            session_id=row.session_id,
            task_id=row.task_id,
            note_type=NoteType(row.note_type),
            content=row.content,
            self_confidence=row.self_confidence,
            ai_evidence_score=float(row.ai_evidence_score)
            if row.ai_evidence_score is not None
            else None,
            alignment_flag=AlignmentFlag(row.alignment_flag),
            verification_status=VerificationStatus(row.verification_status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_by_id(self, session_id: UUID) -> StudySession | None:
        stmt = select(StudySessionORM).where(StudySessionORM.id == session_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(row) if row is not None else None

    async def get_by_id_for_update(self, session_id: UUID) -> StudySession | None:
        stmt = (
            select(StudySessionORM)
            .where(StudySessionORM.id == session_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(row) if row is not None else None

    async def get_active_for_user(self, user_id: UUID) -> StudySession | None:
        stmt = (
            select(StudySessionORM)
            .where(
                StudySessionORM.user_id == user_id,
                StudySessionORM.status == "IN_PROGRESS",
            )
            .order_by(StudySessionORM.started_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(row) if row is not None else None

    async def get_latest_pending_takeaway_for_user(self, user_id: UUID) -> StudySession | None:
        stmt = (
            select(StudySessionORM)
            .where(
                StudySessionORM.user_id == user_id,
                StudySessionORM.pending_takeaway.is_(True),
            )
            .order_by(
                StudySessionORM.ended_at.desc().nulls_last(), StudySessionORM.started_at.desc()
            )
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(row) if row is not None else None

    async def save(self, study_session: StudySession) -> StudySession:
        row = await self._session.get(StudySessionORM, study_session.id)
        now = _ensure_utc(study_session.updated_at)
        created = _ensure_utc(study_session.created_at)
        started = _ensure_utc(study_session.started_at)
        heartbeat = _ensure_utc(study_session.last_heartbeat_at)

        if row is None:
            row = StudySessionORM(
                id=study_session.id,
                user_id=study_session.user_id,
                roadmap_id=study_session.roadmap_id,
                started_at=started,
                ended_at=study_session.ended_at,
                planned_minutes=study_session.planned_minutes,
                actual_minutes=study_session.actual_minutes,
                status=study_session.status.value,
                last_heartbeat_at=heartbeat,
                session_mode=study_session.session_mode.value,
                pending_takeaway=study_session.pending_takeaway,
                checkin_time_sufficiency=(
                    study_session.checkin_time_sufficiency.value
                    if study_session.checkin_time_sufficiency is not None
                    else None
                ),
                checkin_perceived_difficulty=study_session.checkin_perceived_difficulty,
                checkin_focus_level=study_session.checkin_focus_level,
                created_at=created,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.ended_at = study_session.ended_at
            row.planned_minutes = study_session.planned_minutes
            row.actual_minutes = study_session.actual_minutes
            row.status = study_session.status.value
            row.last_heartbeat_at = heartbeat
            row.session_mode = study_session.session_mode.value
            row.pending_takeaway = study_session.pending_takeaway
            row.checkin_time_sufficiency = (
                study_session.checkin_time_sufficiency.value
                if study_session.checkin_time_sufficiency is not None
                else None
            )
            row.checkin_perceived_difficulty = study_session.checkin_perceived_difficulty
            row.checkin_focus_level = study_session.checkin_focus_level
            row.updated_at = now

        try:
            await self._session.flush()
        except IntegrityError as exc:
            err_msg = str(exc.orig or exc)
            if "uq_study_sessions_user_active" in err_msg:
                raise ActiveSessionExistsError() from exc
            raise

        return self._to_domain(row)

    async def upsert_session_task(self, session_task: SessionTask) -> SessionTask:
        stmt = select(SessionTaskORM).where(
            SessionTaskORM.session_id == session_task.session_id,
            SessionTaskORM.task_id == session_task.task_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        now = _ensure_utc(session_task.updated_at)
        created = _ensure_utc(session_task.created_at)

        if row is None:
            row = SessionTaskORM(
                id=session_task.id,
                session_id=session_task.session_id,
                task_id=session_task.task_id,
                allocated_minutes=session_task.allocated_minutes,
                actual_minutes=session_task.actual_minutes,
                status_after_session=session_task.status_after_session,
                notes=session_task.notes,
                created_at=created,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.allocated_minutes = session_task.allocated_minutes
            row.actual_minutes = session_task.actual_minutes
            row.status_after_session = session_task.status_after_session
            row.notes = session_task.notes
            row.updated_at = now

        await self._session.flush()
        return self._st_to_domain(row)

    async def list_session_tasks(self, session_id: UUID) -> list[SessionTask]:
        stmt = (
            select(SessionTaskORM)
            .where(SessionTaskORM.session_id == session_id)
            .order_by(SessionTaskORM.created_at.asc(), SessionTaskORM.id.asc())
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        return [self._st_to_domain(r) for r in rows]

    async def upsert_study_note(self, study_note: StudyNote) -> StudyNote:
        row: StudyNoteORM | None = None
        if study_note.session_id is not None:
            stmt = select(StudyNoteORM).where(
                StudyNoteORM.session_id == study_note.session_id,
                StudyNoteORM.note_type == study_note.note_type.value,
            )
            row = (await self._session.execute(stmt)).scalar_one_or_none()
        else:
            row = await self._session.get(StudyNoteORM, study_note.id)

        now = _ensure_utc(study_note.updated_at)
        created = _ensure_utc(study_note.created_at)

        if row is None:
            row = StudyNoteORM(
                id=study_note.id,
                user_id=study_note.user_id,
                session_id=study_note.session_id,
                task_id=study_note.task_id,
                note_type=study_note.note_type.value,
                content=study_note.content,
                self_confidence=study_note.self_confidence,
                ai_evidence_score=(
                    Decimal(str(study_note.ai_evidence_score))
                    if study_note.ai_evidence_score is not None
                    else None
                ),
                alignment_flag=study_note.alignment_flag.value,
                verification_status=study_note.verification_status.value,
                created_at=created,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.task_id = study_note.task_id
            row.content = study_note.content
            row.self_confidence = study_note.self_confidence
            if study_note.ai_evidence_score is not None:
                row.ai_evidence_score = Decimal(str(study_note.ai_evidence_score))
            row.alignment_flag = study_note.alignment_flag.value
            row.verification_status = study_note.verification_status.value
            row.updated_at = now

        await self._session.flush()
        return self._note_to_domain(row)

    async def get_study_note_for_session(
        self,
        session_id: UUID,
        note_type: NoteType,
    ) -> StudyNote | None:
        stmt = select(StudyNoteORM).where(
            StudyNoteORM.session_id == session_id,
            StudyNoteORM.note_type == note_type.value,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._note_to_domain(row) if row is not None else None

    async def list_study_notes_for_session(self, session_id: UUID) -> list[StudyNote]:
        stmt = (
            select(StudyNoteORM)
            .where(StudyNoteORM.session_id == session_id)
            .order_by(StudyNoteORM.created_at.asc())
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        return [self._note_to_domain(r) for r in rows]
