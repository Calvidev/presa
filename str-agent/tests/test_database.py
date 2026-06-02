"""Integration tests for the Database layer using a temporary SQLite file."""
import datetime
import pytest
from pathlib import Path

from str_agent.database import Database
from str_agent.models import CalendarDay, Listing, MonthlyMetrics


@pytest.fixture
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "test.db")
    d.connect()
    yield d
    d.close()


def _listing(ext_id="abc123", platform="airbnb", city="Miami") -> Listing:
    return Listing(
        external_id  = ext_id,
        platform     = platform,
        city         = city,
        source_url   = f"https://www.airbnb.com/rooms/{ext_id}",
        title        = "Nice apartment",
        rating       = 4.8,
        review_count = 42,
    )


def test_start_and_finish_scrape_run(db):
    run_id = db.start_scrape_run("airbnb", "Miami")
    assert run_id > 0
    db.finish_scrape_run(run_id, listings_found=10, listings_saved=8)

    row = db._conn.execute(
        "SELECT status, listings_found, listings_saved FROM scrape_runs WHERE id=?",
        (run_id,)
    ).fetchone()
    assert row["status"] == "completed"
    assert row["listings_found"] == 10
    assert row["listings_saved"] == 8


def test_upsert_listing_inserts(db):
    run_id = db.start_scrape_run("airbnb", "Miami")
    lid    = db.upsert_listing(_listing(), run_id)
    assert lid > 0

    row = db._conn.execute("SELECT * FROM listings WHERE id=?", (lid,)).fetchone()
    assert row["external_id"] == "abc123"
    assert row["platform"] == "airbnb"
    assert row["city"] == "Miami"
    assert row["scrape_run_id"] == run_id
    assert row["source_url"] == "https://www.airbnb.com/rooms/abc123"


def test_upsert_listing_updates_on_conflict(db):
    run1 = db.start_scrape_run("airbnb", "Miami")
    lid1 = db.upsert_listing(_listing(), run1)

    run2    = db.start_scrape_run("airbnb", "Miami")
    updated = _listing()
    updated.title  = "Updated title"
    updated.rating = 4.9
    lid2 = db.upsert_listing(updated, run2)

    assert lid1 == lid2  # same row
    row = db._conn.execute("SELECT title, rating FROM listings WHERE id=?", (lid1,)).fetchone()
    assert row["title"] == "Updated title"
    assert row["rating"] == 4.9


def test_upsert_calendar_days(db):
    run_id = db.start_scrape_run("airbnb", "Miami")
    lid    = db.upsert_listing(_listing(), run_id)

    days = [
        CalendarDay(listing_id=lid, date=datetime.date(2026, 6, 1),
                    available=True,  price_usd=100.0, scrape_run_id=run_id),
        CalendarDay(listing_id=lid, date=datetime.date(2026, 6, 2),
                    available=False, price_usd=120.0, scrape_run_id=run_id),
    ]
    db.upsert_calendar_days(days)

    rows = db._conn.execute(
        "SELECT date, available, price_usd, scrape_run_id FROM calendar_days "
        "WHERE listing_id=? ORDER BY date", (lid,)
    ).fetchall()
    assert len(rows) == 2
    assert rows[0]["date"] == "2026-06-01"
    assert rows[0]["available"] == 1
    assert rows[0]["price_usd"] == 100.0
    assert rows[0]["scrape_run_id"] == run_id
    assert rows[1]["available"] == 0


def test_upsert_monthly_metrics(db):
    run_id = db.start_scrape_run("airbnb", "Miami")
    lid    = db.upsert_listing(_listing(), run_id)

    m = MonthlyMetrics(
        listing_id=lid, year_month="2026-06",
        nights_available=20, nights_booked=10,
        occupancy_rate=0.333, avg_daily_rate=150.0,
        revpar=50.0, est_revenue=1500.0,
    )
    db.upsert_monthly_metrics(m)

    row = db._conn.execute(
        "SELECT * FROM monthly_metrics WHERE listing_id=?", (lid,)
    ).fetchone()
    assert row["year_month"] == "2026-06"
    assert row["occupancy_rate"] == pytest.approx(0.333)
    assert row["est_revenue"] == 1500.0


def test_get_market_summary(db):
    run_id = db.start_scrape_run("airbnb", "Miami")
    lid    = db.upsert_listing(_listing(), run_id)

    m = MonthlyMetrics(
        listing_id=lid, year_month="2026-06",
        nights_available=10, nights_booked=20,
        occupancy_rate=0.667, avg_daily_rate=200.0,
        revpar=133.4, est_revenue=4000.0,
    )
    db.upsert_monthly_metrics(m)

    rows = db.get_market_summary("Miami")
    assert len(rows) == 1
    assert rows[0]["platform"] == "airbnb"
    assert rows[0]["listings"] == 1
    assert rows[0]["total_est_revenue"] == pytest.approx(4000.0)
