from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import datetime


@dataclass
class Listing:
    external_id:   str
    platform:      str          # 'airbnb' | 'booking' | 'vrbo'
    city:          str
    source_url:    Optional[str] = None
    title:         Optional[str] = None
    neighborhood:  Optional[str] = None
    latitude:      Optional[float] = None
    longitude:     Optional[float] = None
    property_type: Optional[str] = None
    bedrooms:      Optional[int] = None
    bathrooms:     Optional[float] = None
    max_guests:    Optional[int] = None
    amenities:     list[str] = field(default_factory=list)
    host_id:       Optional[str] = None
    is_superhost:  bool = False
    rating:        Optional[float] = None
    review_count:  Optional[int] = None


@dataclass
class CalendarDay:
    listing_id:    int              # FK to listings.id (set after DB insert)
    date:          datetime.date
    available:     bool
    price_usd:     Optional[float] = None
    min_nights:    Optional[int] = None
    scrape_run_id: Optional[int] = None


@dataclass
class MonthlyMetrics:
    listing_id:       int
    year_month:       str           # 'YYYY-MM'
    nights_available: int
    nights_booked:    int
    occupancy_rate:   float
    avg_daily_rate:   float
    revpar:           float
    est_revenue:      float


@dataclass
class ScrapeResult:
    listing:       Listing
    calendar_days: list[CalendarDay] = field(default_factory=list)
