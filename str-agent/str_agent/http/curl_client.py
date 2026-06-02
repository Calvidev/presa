from __future__ import annotations
import asyncio
import logging
import random
from typing import Optional

from ..config import Settings
from ..utils.user_agents import get_random_ua
from .proxy import ProxyPool

log = logging.getLogger(__name__)


class CurlClient:
    """
    Async HTTP client using curl_cffi for TLS fingerprint spoofing.
    Used for Booking.com GraphQL (no browser required).
    """

    def __init__(self, settings: Settings, proxy_pool: ProxyPool):
        self._settings   = settings
        self._proxy_pool = proxy_pool
        self._session    = None

    async def __aenter__(self) -> "CurlClient":
        from curl_cffi.requests import AsyncSession
        proxy = self._proxy_pool.next()
        self._session = AsyncSession(
            impersonate="chrome120",
            proxies=proxy.curl_proxies if proxy else None,
            headers={
                "User-Agent":      get_random_ua(),
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=30,
        )
        return self

    async def __aexit__(self, *args) -> None:
        if self._session:
            await self._session.close()

    async def get(self, url: str, **kwargs) -> dict:
        rl = self._settings.rate_limit
        await asyncio.sleep(random.uniform(rl.min_delay_s, rl.max_delay_s))
        response = await self._session.get(url, **kwargs)
        response.raise_for_status()
        return response

    async def post_json(self, url: str, payload: dict,
                        extra_headers: Optional[dict] = None) -> dict:
        rl = self._settings.rate_limit
        await asyncio.sleep(random.uniform(rl.min_delay_s, rl.max_delay_s))
        headers = {"Content-Type": "application/json", **(extra_headers or {})}
        response = await self._session.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
