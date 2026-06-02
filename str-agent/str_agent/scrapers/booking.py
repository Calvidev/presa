"""
Booking.com scraper — uses curl_cffi (TLS fingerprint spoofing) to call
Booking's internal GraphQL endpoint directly without a browser.

Steps:
  1. GET homepage to extract CSRF token from cookies/meta tag
  2. POST to /dml/graphql with FullSearch query → listing IDs + basic data
  3. POST availability query per listing → calendar days
"""
from __future__ import annotations
import datetime
import logging
import re
from typing import Optional

from ..config import Settings
from ..http.curl_client import CurlClient
from ..models import CalendarDay, Listing, ScrapeResult
from ..utils.rate_limiter import TokenBucketLimiter
from ..utils.retry import async_retry
from .base import BaseScraper

log = logging.getLogger(__name__)

PLATFORM      = "booking"
GRAPHQL_URL   = "https://www.booking.com/dml/graphql"
HOMEPAGE_URL  = "https://www.booking.com/"

_SEARCH_QUERY = """
query FullSearch($input: SearchQueryInput!) {
  searchQueries {
    search(input: $input) {
      results {
        basicPropertyData {
          id
          name
          reviewScore { score reviewCount }
          location { address { city } coordinates { latitude longitude } }
        }
        blocks {
          finalPrice { amount currency }
          minLengthOfStay
        }
      }
    }
  }
}
"""

_AVAIL_QUERY = """
query PropertyAvailability($propertyId: Int!, $checkin: String!, $checkout: String!) {
  property(id: $propertyId) {
    availabilityCalendar(checkin: $checkin, checkout: $checkout) {
      days {
        date
        available
        minLengthOfStay
        price { amount }
      }
    }
  }
}
"""


class BookingScraper(BaseScraper):
    PLATFORM = PLATFORM

    def __init__(self, settings: Settings, limiter: TokenBucketLimiter,
                 curl_client: CurlClient):
        super().__init__(settings, limiter)
        self._client     = curl_client
        self._csrf_token = ""

    async def _refresh_csrf(self) -> None:
        try:
            resp = await self._client.get(HOMEPAGE_URL)
            # Try cookie first
            for cookie in (getattr(resp, "cookies", None) or []):
                name = getattr(cookie, "name", "") or ""
                if "csrf" in name.lower():
                    self._csrf_token = cookie.value
                    return
            # Fallback: look in response text
            text  = getattr(resp, "text", "") or ""
            match = re.search(r'["\']bkng_csrf_token["\']\s*:\s*["\']([\w-]+)', text)
            if match:
                self._csrf_token = match.group(1)
        except Exception as e:
            log.warning("Could not refresh CSRF token: %s", e)

    @async_retry(max_attempts=3)
    async def search_listings(self, city: str, check_in: str,
                               check_out: str) -> list[str]:
        await self._refresh_csrf()
        payload = {
            "operationName": "FullSearch",
            "query": _SEARCH_QUERY,
            "variables": {
                "input": {
                    "dest_type": "city",
                    "query": city,
                    "checkin": check_in,
                    "checkout": check_out,
                    "filter": {"accommodation_type": [201]},
                    "rows": min(self.settings.max_listings, 100),
                }
            },
        }
        extra = {"x-booking-csrf": self._csrf_token} if self._csrf_token else {}
        try:
            data = await self._client.post_json(GRAPHQL_URL, payload, extra)
            ids  = _parse_search_ids(data)
        except Exception as e:
            log.warning("[booking] search error: %s", e)
            ids = []
        log.info("[booking] search '%s': found %d listing IDs", city, len(ids))
        return ids

    @async_retry(max_attempts=3)
    async def fetch_listing(self, listing_id: str, city: str) -> ScrapeResult:
        today     = datetime.date.today()
        check_out = (today + datetime.timedelta(
                         days=self.settings.calendar_days)).isoformat()
        payload = {
            "operationName": "PropertyAvailability",
            "query": _AVAIL_QUERY,
            "variables": {
                "propertyId": int(listing_id),
                "checkin":    today.isoformat(),
                "checkout":   check_out,
            },
        }
        extra = {"x-booking-csrf": self._csrf_token} if self._csrf_token else {}
        source_url = f"https://www.booking.com/hotel/xx/{listing_id}.html"

        try:
            data     = await self._client.post_json(GRAPHQL_URL, payload, extra)
            calendar = _parse_calendar(data)
        except Exception as e:
            log.warning("[booking] fetch error for %s: %s", listing_id, e)
            calendar = []

        listing = Listing(
            external_id = listing_id,
            platform    = PLATFORM,
            city        = city,
            source_url  = source_url,
        )
        return ScrapeResult(listing=listing, calendar_days=calendar)


# ------------------------------------------------------------------ #
#  Parsing helpers                                                     #
# ------------------------------------------------------------------ #

def _parse_search_ids(data: dict) -> list[str]:
    try:
        results = (
            data["data"]["searchQueries"]["search"]["results"]
        )
        return [str(r["basicPropertyData"]["id"]) for r in results]
    except (KeyError, TypeError):
        return []


def _parse_calendar(data: dict) -> list[CalendarDay]:
    try:
        days_raw = (
            data["data"]["property"]["availabilityCalendar"]["days"]
        )
        return [
            CalendarDay(
                listing_id = 0,
                date       = datetime.date.fromisoformat(d["date"]),
                available  = bool(d.get("available", False)),
                price_usd  = (d.get("price") or {}).get("amount"),
                min_nights = d.get("minLengthOfStay"),
            )
            for d in days_raw
            if d.get("date")
        ]
    except (KeyError, TypeError):
        return []
