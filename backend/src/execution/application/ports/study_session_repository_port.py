from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.execution.domain.models.study_session import (
    NoteType,
    SessionTask,
    StudyNote,
    StudySession,
)


class StudySessionRepositoryPort(Protocol):
    """Repository port for StudySession, SessionTask, and StudyNote persistence."""

    async def get_by_id(self, session_id: UUID) -> StudySession | None: ...

    async def get_by_id_for_update(self, session_id: UUID) -> StudySession | None: ...

    async def get_active_for_user(self, user_id: UUID) -> StudySession | None: ...

    async def get_latest_pending_takeaway_for_user(self, user_id: UUID) -> StudySession | None: ...

    async def save(self, study_session: StudySession) -> StudySession: ...

    async def upsert_session_task(self, session_task: SessionTask) -> SessionTask: ...

    async def list_session_tasks(self, session_id: UUID) -> list[SessionTask]: ...

    async def upsert_study_note(self, study_note: StudyNote) -> StudyNote: ...

    async def get_study_note_for_session(
        self,
        session_id: UUID,
        note_type: NoteType,
    ) -> StudyNote | None: ...

    async def list_study_notes_for_session(self, session_id: UUID) -> list[StudyNote]: ...

    async def list_completed_for_user_between(
        self,
        user_id: UUID,
        start_utc: datetime,
        end_utc: datetime,
    ) -> list[StudySession]: ...

    async def list_general_notes_for_user(self, user_id: UUID) -> list[StudyNote]: ...

    async def get_study_note_by_id(self, note_id: UUID) -> StudyNote | None: ...

    async def delete_study_note(self, note_id: UUID) -> None: ...
