from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.account.domain.models.calendar_connection import CalendarConnection


class CalendarConnectionRepositoryPort(Protocol):
    """Driven Port for persisting and querying CalendarConnection Aggregate Root (UC-17)."""

    async def get_by_user_id_and_provider(
        self,
        user_id: UUID,
        provider: str = "GOOGLE",
    ) -> CalendarConnection | None:
        """Find calendar connection for a user and specific provider."""
        ...

    async def get_by_user_id(self, user_id: UUID) -> list[CalendarConnection]:
        """List all calendar connections for a given user."""
        ...

    async def get_by_channel_id(self, channel_id: str) -> CalendarConnection | None:
        """Find active calendar connection by its webhook watch channel ID."""
        ...

    async def get_expiring_active_connections(
        self,
        expiration_before: datetime,
    ) -> list[CalendarConnection]:
        """Find active calendar connections whose webhook channel expires before expiration_before."""
        ...

    async def get_active_connections(self) -> list[CalendarConnection]:
        """Find all active calendar connections."""
        ...

    async def save(self, connection: CalendarConnection) -> CalendarConnection:
        """Persist or update calendar connection aggregate root."""
        ...

    async def delete(self, connection_id: UUID) -> bool:
        """Remove a calendar connection by primary key ID."""
        ...
