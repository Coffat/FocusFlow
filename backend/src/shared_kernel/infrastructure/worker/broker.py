import os
import sys
from collections.abc import Callable, Mapping
from typing import Any

from taskiq import AsyncBroker, InMemoryBroker, TaskiqScheduler
from taskiq.middlewares import SimpleRetryMiddleware
from taskiq.schedule_sources import LabelScheduleSource

from src.shared_kernel.config import get_settings

_dependency_overrides_provider: Callable[[], Mapping[Any, Callable[..., Any]]] | None = None


def register_dependency_overrides_provider(
    provider: Callable[[], Mapping[Any, Callable[..., Any]]],
) -> None:
    """Allow FastAPI app to expose dependency_overrides to worker tasks without circular imports."""
    global _dependency_overrides_provider
    _dependency_overrides_provider = provider


def get_registered_dependency_overrides() -> Mapping[Any, Callable[..., Any]]:
    if _dependency_overrides_provider is None:
        return {}
    return _dependency_overrides_provider()


settings = get_settings()


def _is_test_runtime() -> bool:
    return (
        settings.environment == "test"
        or "PYTEST_CURRENT_TEST" in os.environ
        or "pytest" in sys.modules
    )


broker: AsyncBroker
try:
    from taskiq_redis import RedisStreamBroker

    broker = InMemoryBroker() if _is_test_runtime() else RedisStreamBroker(url=settings.redis_url)
except ImportError:  # pragma: no cover
    broker = InMemoryBroker()

broker = broker.with_middlewares(SimpleRetryMiddleware(default_retry_count=3))

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
