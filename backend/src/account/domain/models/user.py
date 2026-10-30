from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    """Domain model representing a registered user / learner in the Account context."""

    id: UUID
    email: str
    password_hash: str
    full_name: str
    timezone: str = "Asia/Ho_Chi_Minh"
    role: str = "LEARNER"
    tier: str = "FREE"
    is_locked: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def is_account_locked(self) -> bool:
        """Domain rule: checks whether account has been suspended or locked."""
        return self.role == "LOCKED" or self.is_locked

    def is_admin(self) -> bool:
        return self.role == "ADMIN"
