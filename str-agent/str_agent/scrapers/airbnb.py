"""
Airbnb scraper — uses Playwright network interception to capture internal
GraphQL/JSON API responses instead of parsing HTML (more resilient to
CSS class churn).

Key intercepted endpoints:
  StaysSearch          → listing IDs from search results
  PdpPlatformSections  → listing detail (title, rating, amenities, location)
  PdpAvailabilityCalendar → per-day availability + price
"""
from __future__ import annotations
import asyncio
import datetime
import logging
import re
from typing import Optional

from playwright.async_api import Route, Request

from ..config import Settings
from ..http.browser import BrowserPool
from ..models import CalendarDay, Listing, ScrapeResult
from ..utils.rate_limiter import TokenBucketLimiter
from ..utils.retry import async_retry
from .base import BaseScraper

log = logging.getLogger(__name__)

PLATFORM = "airbnb"


class AirbnbScraper(BaseScraper):
    PLATFORM = PLATFORM

    def __init__(self, settings: Settings, limiter: TokenBucketLimiter,
                 browser_pool: BrowserPool):
        super().__init__(settings, limiter)
        self._browser = browser_pool

    @async_retry(max_attempts=3)
    async def search_listings(self, city: str, check_in: str,
                               check_out: str) -> list[str]:
        captured_ids: list[str] = []
        done = asyncio.Event()

        async with self._browser.new_context() as ctx:
            page = await ctx.new_page()

            async def handle(route: Route, request: Request) -> None:
                if "StaysSearch" in request.url:
                    response = await route.fetch()
                    try:
                        body = await response.json()
                        ids  = _parse_stays_search_ids(body)
                        captured_ids.extend(ids)
                    except Exception as e:
                        log.debug("StaysSearch parse error: %s", e)
                    done.set()
                    await route.fulfill(response=response)
                else:
                    await route.continue_()

            await page.route("**/api/v3/**", handle)

            slug = city.replace(" ", "-").lower().replace(",", "")
            url  = (f"https://www.airbnb.com/s/{slug}/homes"
                    f"?checkin={check_in}&checkout={check_out}")
            await page.goto(url, wait_until="networkidle", timeout=45_000)

            # Trigger pagination via scroll
            for _ in range(3):
                await page.keyboard.press("End")
                await asyncio.sleep(1.5)

        log.info("[airbnb] search '%s': found %d listing IDs", city, len(captured_ids))
        return list(dict.fromkeys(captured_ids))

    @async_retry(max_attempts=3)
    async def fetch_listing(self, listing_id: str, city: str) -> ScrapeResult:
        captured_sections: dict = {}
        captured_calendar: list = []

        async with self._browser.new_context() as ctx:
            page = await ctx.new_page()

            async def handle(route: Route, request: Request) -> None:
                if "PdpPlatformSections" in request.url:
                    response = await route.fetch()
                    try:
                        body = await response.json()
                        captured_sections.update(body)
                    except Exception as e:
                        log.debug("PdpPlatformSections parse error: %s", e)
                    await route.fulfill(response=response)
                elif "PdpAvailabilityCalendar" in request.url:
                    response = await route.fetch()
                    try:
                        body = await response.json()
                        months = (
                            body.get("data", {})
                                .get("merlin", {})
                                .get("pdpAvailabilityCalendar", {})
                                .get("calendarMonths", [])
                        )
                        captured_calendar.extend(months)
                    except Exception as e:
                        log.debug("Calendar parse error: %s", e)
                    await route.fulfill(response=response)
                else:
                    await route.continue_()

            await page.route("**/api/v3/**", handle)

            source_url = f"https://www.airbnb.com/rooms/{listing_id}"
            await page.goto(source_url, wait_until="networkidle", timeout=45_000)

        listing  = _parse_pdp_sections(listing_id, city, source_url, captured_sections)
        calendar = _parse_calendar_months(captured_calendar)
        return ScrapeResult(listing=listing, calendar_days=calendar)


# ------------------------------------------------------------------ #
#  Parsing helpers (pure functions — easy to unit-test)               #
# ------------------------------------------------------------------ #

def _parse_stays_search_ids(body: dict) -> list[str]:
    try:
        results = (
            body["data"]["presentation"]["staysSearch"]
                ["results"]["searchResults"]
        )
        return [s["listing"]["id"] for s in results if "listing" in s]
    except (KeyError, TypeError):
        return []


def _parse_pdp_sections(listing_id: str, city: str,
                         source_url: str, body: dict) -> Listing:
    try:
        sections = (
            body.get("data", {})
                .get("presentation", {})
                .get("stayProductDetailPage", {})
                .get("sections", {})
                .get("sections", [])
        )
        title        = None
        rating       = None
        review_count = None
        lat          = None
        lon          = None
        bedrooms     = None
        max_guests   = None
        amenities    = []
        host_id      = None
        is_superhost = False

        for section in sections:
            stype = section.get("sectionComponentType", "")
            data  = section.get("sectionData", {}) or {}

            if stype == "LISTING_TITLE" and not title:
                title = data.get("title")

            if stype in ("OVERVIEW_DEFAULT", "OVERVIEW_DEFAULT_V2"):
                rating       = data.get("overallRating") or rating
                review_count = data.get("reviewCount") or review_count

            if stype == "LOCATION_DEFAULT":
                loc = data.get("location", {}) or {}
                lat = loc.get("lat")
                lon = loc.get("lng")

            if stype == "AMENITIES_DEFAULT":
                for group in (data.get("seeAllAmenitiesGroups") or []):
                    for item in (group.get("amenities") or []):
                        name = item.get("title")
                        if name:
                            amenities.append(name)

            if "OVERVIEW" in stype:
                for item in (data.get("overviewItems") or []):
                    text = (item.get("title") or "").lower()
                    if "bedroom" in text:
                        m = re.search(r"\d+", text)
                        if m:
                            bedrooms = int(m.group())
                    if "guest" in text:
                        m = re.search(r"\d+", text)
                        if m:
                            max_guests = int(m.group())

        return Listing(
            external_id  = listing_id,
            platform     = PLATFORM,
            city         = city,
            source_url   = source_url,
            title        = title,
            latitude     = lat,
            longitude    = lon,
            bedrooms     = bedrooms,
            max_guests   = max_guests,
            amenities    = amenities,
            host_id      = host_id,
            is_superhost = is_superhost,
            rating       = rating,
            review_count = review_count,
        )
    except Exception as e:
        log.warning("PDP parse error for listing %s: %s", listing_id, e)
        return Listing(
            external_id = listing_id,
            platform    = PLATFORM,
            city        = city,
            source_url  = source_url,
        )


def _parse_calendar_months(months: list) -> list[CalendarDay]:
    days: list[CalendarDay] = []
    for month in months:
        for week in (month.get("weeks") or []):
            for day in (week.get("days") or []):
                date_str = day.get("calendarDate")
                if not date_str:
                    continue
                price_str = (
                    (day.get("price") or {})
                    .get("localPriceFormatted", "") or ""
                )
                days.append(CalendarDay(
                    listing_id = 0,
                    date       = datetime.date.fromisoformat(date_str),
                    available  = bool(day.get("available", False)),
                    price_usd  = _parse_price(price_str),
                    min_nights = day.get("minNights"),
                ))
    return days


def _parse_price(price_str: str) -> Optional[float]:
    cleaned = re.sub(r"[^\d.]", "", price_str.replace(",", ""))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None
