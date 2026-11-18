from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any


async def call_for_update[T](
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    **kwargs: Any,
) -> T:
    """Invoke a repository method with `for_update=True` when supported by its signature."""
    if "for_update" in inspect.signature(fn).parameters:
        return await fn(*args, for_update=True, **kwargs)
    return await fn(*args, **kwargs)
