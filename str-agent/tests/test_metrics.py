import datetime
import pytest

from str_agent.metrics import compute_monthly_metrics
from str_agent.models import CalendarDay


def _day(date_str: str, available: bool, price: float = None) -> CalendarDay:
    return CalendarDay(
        listing_id=1,
        date=datetime.date.fromisoformat(date_str),
        available=available,
        price_usd=price,
    )


def test_empty_returns_empty():
    assert compute_monthly_metrics(1, []) == []


def test_full_month_booked():
    # All 30 days of June 2026 booked at $100/night
    days = [_day(f"2026-06-{d:02d}", False, 100.0) for d in range(1, 31)]
    metrics = compute_monthly_metrics(1, days)
    assert len(metrics) == 1
    m = metrics[0]
    assert m.year_month == "2026-06"
    assert m.nights_booked == 30
    assert m.nights_available == 0
    assert abs(m.occupancy_rate - 1.0) < 0.01
    assert m.avg_daily_rate == 100.0
    assert m.revpar == 100.0
    assert m.est_revenue == 3000.0


def test_half_month_booked():
    # 15 booked, 15 available in June (30 days)
    days = (
        [_day(f"2026-06-{d:02d}", False, 200.0) for d in range(1, 16)]
        + [_day(f"2026-06-{d:02d}", True,  None) for d in range(16, 31)]
    )
    metrics = compute_monthly_metrics(1, days)
    m = metrics[0]
    assert abs(m.occupancy_rate - 0.5) < 0.01
    assert m.avg_daily_rate == 200.0
    assert abs(m.revpar - 100.0) < 0.01
    assert m.est_revenue == 3000.0


def test_no_prices_gives_zero_adr():
    days = [_day(f"2026-07-{d:02d}", False, None) for d in range(1, 11)]
    metrics = compute_monthly_metrics(1, days)
    m = metrics[0]
    assert m.avg_daily_rate == 0.0
    assert m.revpar == 0.0
    assert m.est_revenue == 0.0


def test_multiple_months():
    days = (
        [_day(f"2026-06-{d:02d}", False, 150.0) for d in range(1, 11)]
        + [_day(f"2026-07-{d:02d}", False, 250.0) for d in range(1, 16)]
    )
    metrics = compute_monthly_metrics(1, days)
    assert len(metrics) == 2
    assert metrics[0].year_month == "2026-06"
    assert metrics[1].year_month == "2026-07"


def test_listing_id_set_correctly():
    days = [_day("2026-06-01", False, 100.0)]
    metrics = compute_monthly_metrics(42, days)
    assert metrics[0].listing_id == 42
