from typing import Any

from src.account.infrastructure.adapters.availability_query_adapter import (
    SqlAlchemyAvailabilityQueryAdapter,
)
from src.account.infrastructure.adapters.calendar_connection_query_adapter import (
    SqlAlchemyCalendarConnectionQueryAdapter,
)
from src.account.infrastructure.adapters.google_calendar_adapter import (
    GoogleCalendarAdapter,
)
from src.account.infrastructure.adapters.learner_profile_query_adapter import (
    LearnerProfileQueryAdapter,
    SqlAlchemyLearnerProfileQueryAdapter,
)
from src.account.infrastructure.adapters.mock_calendar_adapter import (
    MockCalendarAdapter,
)
from src.account.infrastructure.adapters.quota_facade_adapter import (
    QuotaFacadeAdapter,
    SqlAlchemyQuotaFacadeAdapter,
)
from src.account.infrastructure.adapters.user_query_adapter import (
    SqlAlchemyUserQueryAdapter,
    UserQueryAdapter,
)
from src.account.infrastructure.repositories.availability_repository import (
    SqlAlchemyAvailabilityRepository,
)
from src.account.infrastructure.repositories.calendar_connection_repository import (
    SqlAlchemyCalendarConnectionRepository,
)
from src.account.public_api import register_account_port_factories


def _create_availability_query(session: Any) -> SqlAlchemyAvailabilityQueryAdapter:
    return SqlAlchemyAvailabilityQueryAdapter(repository=SqlAlchemyAvailabilityRepository(session))


def _create_calendar_connection_query(
    session: Any,
    calendar_provider: Any = None,
) -> SqlAlchemyCalendarConnectionQueryAdapter:
    if calendar_provider is None:
        from src.shared_kernel.config import get_settings

        settings = get_settings()
        if settings.calendar_provider.strip().lower() in ("mock", "local_mock"):
            calendar_provider = MockCalendarAdapter()
        else:
            calendar_provider = GoogleCalendarAdapter(settings=settings)
    repo = SqlAlchemyCalendarConnectionRepository(session)
    return SqlAlchemyCalendarConnectionQueryAdapter(
        repository=repo,
        calendar_provider=calendar_provider,
    )


register_account_port_factories(
    quota_factory=QuotaFacadeAdapter,
    availability_factory=_create_availability_query,
    learner_profile_factory=LearnerProfileQueryAdapter,
    user_query_factory=SqlAlchemyUserQueryAdapter,
    calendar_connection_query_factory=_create_calendar_connection_query,
)

__all__ = [
    "GoogleCalendarAdapter",
    "LearnerProfileQueryAdapter",
    "MockCalendarAdapter",
    "QuotaFacadeAdapter",
    "SqlAlchemyAvailabilityQueryAdapter",
    "SqlAlchemyCalendarConnectionQueryAdapter",
    "SqlAlchemyLearnerProfileQueryAdapter",
    "SqlAlchemyQuotaFacadeAdapter",
    "SqlAlchemyUserQueryAdapter",
    "UserQueryAdapter",
]
