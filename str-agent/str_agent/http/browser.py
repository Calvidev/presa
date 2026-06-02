from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext

from ..config import Settings
from ..utils.user_agents import get_random_ua
from .proxy import ProxyPool, ProxyEntry

log = logging.getLogger(__name__)

# Removes the most common automation fingerprints
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
window.chrome = {runtime: {}};
"""


class BrowserPool:
    def __init__(self, settings: Settings, proxy_pool: ProxyPool):
        self._settings   = settings
        self._proxy_pool = proxy_pool
        self._playwright = None
        self._browser: Optional[Browser] = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._settings.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        log.info("Browser started (headless=%s)", self._settings.headless)

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    @asynccontextmanager
    async def new_context(self) -> BrowserContext:
        proxy_entry: Optional[ProxyEntry] = self._proxy_pool.next()
        proxy_cfg = {"server": proxy_entry.playwright_url} if proxy_entry else None

        context = await self._browser.new_context(
            user_agent=get_random_ua(),
            proxy=proxy_cfg,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
            },
        )
        await context.add_init_script(_STEALTH_SCRIPT)
        try:
            yield context
        finally:
            await context.close()
