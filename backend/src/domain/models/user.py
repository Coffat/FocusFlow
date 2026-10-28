from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    id: UUID
    email: str
    password_hash: str
    full_name: str
    timezone: str = "Asia/Ho_Chi_Minh"
    role: str = "LEARNER"
    tier: str = "FREE"
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    def is_locked(self) -> bool:
        """Domain rule: checks whether account has been suspended or locked."""
        return self.role == "LOCKED"

    def is_admin(self) -> bool:
        return self.role == "ADMIN"
