from taskiq import InMemoryBroker, TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from src.shared_kernel.config import get_settings

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
