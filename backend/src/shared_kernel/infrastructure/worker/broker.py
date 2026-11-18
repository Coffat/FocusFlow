from collections.abc import Callable, Mapping
from typing import Any

from taskiq import InMemoryBroker, TaskiqScheduler
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

try:
    from taskiq_redis import RedisStreamBroker

    broker = (
        InMemoryBroker()
        if settings.environment == "test"
        else RedisStreamBroker(url=settings.redis_url)
    )
except ImportError:  # pragma: no cover
    broker = InMemoryBroker()

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
