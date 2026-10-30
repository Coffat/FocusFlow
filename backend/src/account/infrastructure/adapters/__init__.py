from typing import Any

from src.account.infrastructure.adapters.availability_query_adapter import (
    SqlAlchemyAvailabilityQueryAdapter,
)
from src.account.infrastructure.adapters.learner_profile_query_adapter import (
    LearnerProfileQueryAdapter,
    SqlAlchemyLearnerProfileQueryAdapter,
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
from src.account.public_api import register_account_port_factories


def _create_availability_query(session: Any) -> SqlAlchemyAvailabilityQueryAdapter:
    return SqlAlchemyAvailabilityQueryAdapter(repository=SqlAlchemyAvailabilityRepository(session))


register_account_port_factories(
    quota_factory=QuotaFacadeAdapter,
    availability_factory=_create_availability_query,
    learner_profile_factory=LearnerProfileQueryAdapter,
    user_query_factory=SqlAlchemyUserQueryAdapter,
)

__all__ = [
    "LearnerProfileQueryAdapter",
    "QuotaFacadeAdapter",
    "SqlAlchemyAvailabilityQueryAdapter",
    "SqlAlchemyLearnerProfileQueryAdapter",
    "SqlAlchemyQuotaFacadeAdapter",
    "SqlAlchemyUserQueryAdapter",
    "UserQueryAdapter",
]
