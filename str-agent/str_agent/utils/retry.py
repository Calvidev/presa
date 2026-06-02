import asyncio
import functools
import logging
import random

log = logging.getLogger(__name__)


def async_retry(max_attempts: int = 3, base_delay: float = 2.0,
                exceptions: tuple = (Exception,)):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        raise
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                    log.warning(
                        "%s attempt %d/%d failed: %s. Retrying in %.1fs",
                        func.__name__, attempt, max_attempts, exc, delay,
                    )
                    await asyncio.sleep(delay)
        return wrapper
    return decorator
