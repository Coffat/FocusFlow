from datetime import UTC, datetime
from uuid import UUID

from src.account.application.dtos.notifications import (
    MarkAllNotificationsReadResponseDTO,
    NotificationItemDTO,
    NotificationListResponseDTO,
)
from src.account.application.ports.notification_repository_port import (
    NotificationRecordDTO,
    NotificationRepositoryPort,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.domain.exceptions import DomainError


class NotificationNotFoundError(DomainError):
    """Raised when a notification does not exist or does not belong to the authenticated user."""

    def __init__(self, message: str = "Notification not found") -> None:
        super().__init__(message=message, code="NOTIFICATION_NOT_FOUND")


def _record_to_item_dto(record: NotificationRecordDTO) -> NotificationItemDTO:
    return NotificationItemDTO(
        id=record.id,
        notification_type=record.notification_type,
        title=record.title,
        content=record.content,
        resource_url=record.resource_url,
        is_read=record.is_read,
        read_at=record.read_at,
        created_at=record.created_at,
    )


class PersistNotificationUseCase:
    """Persist a notification idempotently (deduplicated by user_id + event_id + type)."""

    def __init__(
        self,
        *,
        notification_repo: NotificationRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._notification_repo = notification_repo
        self._uow = uow

    async def execute(
        self,
        *,
        user_id: UUID,
        notification_type: str,
        title: str,
        content: str,
        event_id: UUID | None = None,
        resource_url: str | None = None,
    ) -> NotificationItemDTO | None:
        async with self._uow:
            created = await self._notification_repo.create_idempotent(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                content=content,
                event_id=event_id,
                resource_url=resource_url,
            )
            await self._uow.commit()
        return _record_to_item_dto(created) if created is not None else None


class ListNotificationsUseCase:
    """List persistent notifications for the authenticated learner."""

    def __init__(self, *, notification_repo: NotificationRepositoryPort) -> None:
        self._notification_repo = notification_repo

    async def execute(
        self,
        *,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
    ) -> NotificationListResponseDTO:
        records, total, unread_count = await self._notification_repo.list_for_user(
            user_id,
            limit=limit,
            offset=offset,
            unread_only=unread_only,
        )
        return NotificationListResponseDTO(
            items=[_record_to_item_dto(rec) for rec in records],
            total=total,
            unread_count=unread_count,
        )


class MarkNotificationReadUseCase:
    """Mark a single notification as read with strict IDOR ownership check."""

    def __init__(
        self,
        *,
        notification_repo: NotificationRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._notification_repo = notification_repo
        self._uow = uow

    async def execute(
        self,
        *,
        notification_id: UUID,
        user_id: UUID,
        now: datetime | None = None,
    ) -> NotificationItemDTO:
        effective_now = now or datetime.now(UTC)
        async with self._uow:
            updated = await self._notification_repo.mark_read(
                notification_id,
                user_id,
                now=effective_now,
            )
            if updated is None:
                raise NotificationNotFoundError("Notification not found")
            await self._uow.commit()
        return _record_to_item_dto(updated)


class MarkAllNotificationsReadUseCase:
    """Mark all unread notifications for the authenticated learner as read."""

    def __init__(
        self,
        *,
        notification_repo: NotificationRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._notification_repo = notification_repo
        self._uow = uow

    async def execute(
        self,
        *,
        user_id: UUID,
        now: datetime | None = None,
    ) -> MarkAllNotificationsReadResponseDTO:
        effective_now = now or datetime.now(UTC)
        async with self._uow:
            updated_count = await self._notification_repo.mark_all_read(
                user_id,
                now=effective_now,
            )
            await self._uow.commit()
        return MarkAllNotificationsReadResponseDTO(updated_count=updated_count)
