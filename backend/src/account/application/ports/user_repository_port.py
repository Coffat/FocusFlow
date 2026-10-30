from typing import Any, Protocol
from uuid import UUID


class UserRepositoryPort(Protocol):
    """Protocol for User and AI Quota persistence operations in Account context."""

    async def find_by_email(self, email: str) -> Any | None:
        """Query user record by email address."""
        ...

    async def find_by_id(self, user_id: UUID) -> Any | None:
        """Query user record by unique identifier."""
        ...

    async def create_user_with_quota(
        self,
        user: Any,
        quota: Any = None,
    ) -> Any:
        """Atomically persist a new user entity and default AI quota allocation."""
        ...

    async def update_password(self, user_id: UUID, password_hash: str) -> None:
        """Update password hash for an existing user."""
        ...
