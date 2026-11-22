import os

import pytest

# QA-GATE-01: Force test environment before any src.* module is imported.
os.environ["ENVIRONMENT"] = "test"
if not os.path.exists("/.dockerenv") and (
    os.environ.get("REDIS_HOST", "") in ("", "redis")
    or "redis:6379" in os.environ.get("REDIS_URL", "")
):
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"


@pytest.fixture(scope="session", autouse=True)
def _verify_test_environment_isolation() -> None:
    """Fail fast if test suite is misconfigured against a non-test environment or real broker."""
    from taskiq import InMemoryBroker

    from src.shared_kernel.config import get_settings
    from src.shared_kernel.infrastructure.worker.broker import broker

    get_settings.cache_clear()
    assert get_settings().environment == "test"
    assert isinstance(broker, InMemoryBroker), (
        f"Test broker must be InMemoryBroker, got {type(broker)}"
    )
