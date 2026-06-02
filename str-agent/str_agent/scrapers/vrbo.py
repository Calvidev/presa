"""
VRBO scraper — uses Playwright network interception since VRBO has no
accessible public or undocumented JSON API.

Intercepted endpoints:
  /api/search or SERP requests → listing IDs
  /api/property/{id}           → listing detail
  URLs containing 'availability' → calendar days
"""
from __future__ import annotations
import asyncio
import datetime
import logging
from typing import Optional

from playwright.async_api import Route, Request

from ..config import Settings
from ..http.browser import BrowserPool
from ..models import CalendarDay, Listing, ScrapeResult
from ..utils.rate_limiter import TokenBucketLimiter
from ..utils.retry import async_retry
from .base import BaseScraper

log = logging.getLogger(__name__)

PLATFORM = "vrbo"


class VrboScraper(BaseScraper):
    PLATFORM = PLATFORM

    def __init__(self, settings: Settings, limiter: TokenBucketLimiter,
                 browser_pool: BrowserPool):
        super().__init__(settings, limiter)
        self._browser = browser_pool

    @async_retry(max_attempts=3)
    async def search_listings(self, city: str, check_in: str,
                               check_out: str) -> list[str]:
        captured: list[str] = []

        async with self._browser.new_context() as ctx:
            page = await ctx.new_page()

            async def handle(route: Route, request: Request) -> None:
                url = request.url
                if "/api/search" in url or "propertyResults" in url:
                    response = await route.fetch()
                    try:
                        body = await response.json()
                        captured.extend(_parse_search_ids(body))
                    except Exception as e:
                        log.debug("VRBO search parse error: %s", e)
                    await route.fulfill(response=response)
                else:
                    await route.continue_()

            await page.route("**/*", handle)

            slug = city.lower().replace(" ", "-").replace(",", "")
            url  = (f"https://www.vrbo.com/vacation-rentals/{slug}"
                    f"?startDate={check_in}&endDate={check_out}")
            await page.goto(url, wait_until="networkidle", timeout=45_000)

            for _ in range(3):
                await page.keyboard.press("End")
                await asyncio.sleep(2.0)

        log.info("[vrbo] search '%s': found %d listing IDs", city, len(captured))
        return list(dict.fromkeys(captured))

    @async_retry(max_attempts=3)
    async def fetch_listing(self, listing_id: str, city: str) -> ScrapeResult:
        captured_detail: dict  = {}
        captured_avail:  list  = []

        async with self._browser.new_context() as ctx:
            page = await ctx.new_page()

            async def handle(route: Route, request: Request) -> None:
                url = request.url
                if f"/property/{listing_id}" in url:
                    response = await route.fetch()
                    try:
                        body = await response.json()
                        captured_detail.update(body)
                    except Exception as e:
                        log.debug("VRBO detail parse error: %s", e)
                    await route.fulfill(response=response)
                elif "availability" in url.lower():
                    response = await route.fetch()
                    try:
                        body = await response.json()
                        captured_avail.extend(
                            body.get("availabilityDates", [])
                            or body.get("days", [])
                        )
                    except Exception as e:
                        log.debug("VRBO availability parse error: %s", e)
                    await route.fulfill(response=response)
                else:
                    await route.continue_()

            await page.route("**/*", handle)
            source_url = f"https://www.vrbo.com/{listing_id}"
            await page.goto(source_url, wait_until="networkidle", timeout=45_000)

        listing  = _parse_detail(listing_id, city, source_url, captured_detail)
        calendar = _parse_calendar(captured_avail)
        return ScrapeResult(listing=listing, calendar_days=calendar)


# ------------------------------------------------------------------ #
#  Parsing helpers                                                     #
# ------------------------------------------------------------------ #

def _parse_search_ids(body: dict) -> list[str]:
    # VRBO response shapes vary; try common patterns
    for key in ("propertyResults", "results", "listings"):
        results = body.get(key, [])
        if results:
            ids = []
            for r in results:
                pid = r.get("propertyId") or r.get("id") or r.get("listingId")
                if pid:
                    ids.append(str(pid))
            if ids:
                return ids
    return []


def _parse_detail(listing_id: str, city: str,
                   source_url: str, body: dict) -> Listing:
    return Listing(
        external_id  = listing_id,
        platform     = PLATFORM,
        city         = city,
        source_url   = source_url,
        title        = body.get("headline") or body.get("name"),
        bedrooms     = body.get("bedrooms") or body.get("bedroomCount"),
        max_guests   = body.get("maxOccupancy") or body.get("sleeps"),
        rating       = body.get("avgRating") or body.get("rating"),
        review_count = body.get("reviewCount") or body.get("reviews"),
    )


def _parse_calendar(avail_dates: list) -> list[CalendarDay]:
    days = []
    for d in avail_dates:
        date_str = d.get("date") or d.get("calendarDate")
        if not date_str:
            continue
        try:
            days.append(CalendarDay(
                listing_id = 0,
                date       = datetime.date.fromisoformat(date_str[:10]),
                available  = bool(d.get("available", False)),
                price_usd  = d.get("amount") or d.get("price"),
            ))
        except ValueError:
            continue
    return days
