import asyncio
import logging
import random
import time

from ..config import RateLimitConfig

log = logging.getLogger(__name__)


class TokenBucketLimiter:
    """Async token bucket with human-like jitter to avoid bot-pattern detection."""

    def __init__(self, config: RateLimitConfig):
        self._config      = config
        self._tokens      = float(config.requests_per_minute)
        self._capacity    = float(config.requests_per_minute)
        self._refill_rate = self._capacity / 60.0   # tokens per second
        self._last_refill = time.monotonic()
        self._lock        = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            self._refill()
            while self._tokens < 1.0:
                await asyncio.sleep(0.5)
                self._refill()
            self._tokens -= 1.0

        jitter = random.uniform(0, self._config.jitter_s)
        base   = random.uniform(self._config.min_delay_s, self._config.max_delay_s)
        await asyncio.sleep(base + jitter)

    def _refill(self) -> None:
        now           = time.monotonic()
        delta         = now - self._last_refill
        self._tokens  = min(self._capacity, self._tokens + delta * self._refill_rate)
        self._last_refill = now
