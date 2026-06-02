from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncIterator

from ..config import Settings
from ..models import ScrapeResult
from ..utils.rate_limiter import TokenBucketLimiter


class BaseScraper(ABC):
    PLATFORM: str = ""

    def __init__(self, settings: Settings, limiter: TokenBucketLimiter):
        self.settings = settings
        self.limiter  = limiter

    @abstractmethod
    async def search_listings(self, city: str, check_in: str,
                               check_out: str) -> list[str]:
        """Return list of external listing IDs for the given city and dates."""
        ...

    @abstractmethod
    async def fetch_listing(self, listing_id: str, city: str) -> ScrapeResult:
        """Fetch full detail + calendar for a single listing."""
        ...

    async def scrape_city(
        self, city: str, check_in: str, check_out: str
    ) -> AsyncIterator[ScrapeResult]:
        listing_ids = await self.search_listings(city, check_in, check_out)
        for lid in listing_ids[: self.settings.max_listings]:
            await self.limiter.acquire()
            result = await self.fetch_listing(lid, city)
            yield result
