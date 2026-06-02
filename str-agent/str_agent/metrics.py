from __future__ import annotations
import calendar
import logging
from collections import defaultdict

from .models import CalendarDay, MonthlyMetrics

log = logging.getLogger(__name__)


def compute_monthly_metrics(
    listing_id: int, days: list[CalendarDay]
) -> list[MonthlyMetrics]:
    """
    Groups CalendarDay records by YYYY-MM and computes AirDNA-style metrics:
      occupancy_rate  = nights_booked / days_in_month
      ADR             = avg nightly price on booked nights
      RevPAR          = occupancy_rate × ADR
      est_revenue     = nights_booked × ADR
    """
    by_month: dict[str, list[CalendarDay]] = defaultdict(list)
    for day in days:
        by_month[day.date.strftime("%Y-%m")].append(day)

    results = []
    for ym, month_days in sorted(by_month.items()):
        year, month = map(int, ym.split("-"))
        days_in_month = calendar.monthrange(year, month)[1]

        booked = [d for d in month_days if not d.available]
        avail  = [d for d in month_days if d.available]

        nights_booked    = len(booked)
        nights_available = len(avail)

        priced = [d.price_usd for d in booked if d.price_usd is not None]
        adr    = sum(priced) / len(priced) if priced else 0.0
        occ    = nights_booked / days_in_month

        results.append(MonthlyMetrics(
            listing_id       = listing_id,
            year_month       = ym,
            nights_available = nights_available,
            nights_booked    = nights_booked,
            occupancy_rate   = round(occ, 4),
            avg_daily_rate   = round(adr, 2),
            revpar           = round(occ * adr, 2),
            est_revenue      = round(nights_booked * adr, 2),
        ))

    return results
