import asyncio
import time
import random


class RateLimiter:
    """Token bucket rate limiter for polite API requests."""

    def __init__(self, rate: float = 3.0, jitter: float = 0.2):
        """
        rate: max requests per second (default 3)
        jitter: random delay factor, ±20% by default to avoid looking like a bot
        """
        self._interval = 1.0 / rate
        self._jitter = jitter
        self._last_acquire = 0.0

    async def acquire(self):
        """Wait until a token is available."""
        now = time.monotonic()
        elapsed = now - self._last_acquire
        if elapsed < self._interval:
            delay = self._interval - elapsed
            # Add jitter: ±jitter% random variation
            jitter_amount = delay * self._jitter * (random.random() * 2 - 1)
            delay += jitter_amount
            if delay > 0:
                await asyncio.sleep(delay)
        self._last_acquire = time.monotonic()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *args):
        pass
