from __future__ import annotations
import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from .models import CalendarDay, Listing, MonthlyMetrics

log = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._run_migrations()
        log.info("Database ready at %s", self.db_path)

    def close(self) -> None:
        if self._conn:
            self._conn.close()

    @contextmanager
    def transaction(self):
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    # ------------------------------------------------------------------ #
    #  Scrape run audit log                                                #
    # ------------------------------------------------------------------ #

    def start_scrape_run(self, platform: str, city: str) -> int:
        with self.transaction():
            row = self._conn.execute(
                "INSERT INTO scrape_runs (platform, city, status) "
                "VALUES (?, ?, 'running') RETURNING id",
                (platform, city),
            ).fetchone()
        log.info("Started scrape run #%d for %s/%s", row["id"], platform, city)
        return row["id"]

    def finish_scrape_run(
        self, run_id: int, listings_found: int,
        listings_saved: int, error_msg: str = None
    ) -> None:
        status = "failed" if error_msg else "completed"
        with self.transaction():
            self._conn.execute(
                "UPDATE scrape_runs SET status=?, listings_found=?, "
                "listings_saved=?, error_msg=?, finished_at=datetime('now') "
                "WHERE id=?",
                (status, listings_found, listings_saved, error_msg, run_id),
            )

    # ------------------------------------------------------------------ #
    #  Listings                                                            #
    # ------------------------------------------------------------------ #

    def upsert_listing(self, listing: Listing, scrape_run_id: int) -> int:
        sql = """
        INSERT INTO listings (
            external_id, platform, scrape_run_id, source_url, title, city,
            neighborhood, latitude, longitude, property_type, bedrooms,
            bathrooms, max_guests, amenities, host_id, is_superhost,
            rating, review_count, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
        ON CONFLICT(external_id, platform) DO UPDATE SET
            scrape_run_id = excluded.scrape_run_id,
            source_url    = excluded.source_url,
            title         = excluded.title,
            neighborhood  = excluded.neighborhood,
            latitude      = excluded.latitude,
            longitude     = excluded.longitude,
            property_type = excluded.property_type,
            bedrooms      = excluded.bedrooms,
            bathrooms     = excluded.bathrooms,
            max_guests    = excluded.max_guests,
            amenities     = excluded.amenities,
            host_id       = excluded.host_id,
            is_superhost  = excluded.is_superhost,
            rating        = excluded.rating,
            review_count  = excluded.review_count,
            updated_at    = datetime('now')
        RETURNING id
        """
        with self.transaction():
            row = self._conn.execute(sql, (
                listing.external_id, listing.platform, scrape_run_id,
                listing.source_url, listing.title, listing.city,
                listing.neighborhood, listing.latitude, listing.longitude,
                listing.property_type, listing.bedrooms, listing.bathrooms,
                listing.max_guests, json.dumps(listing.amenities),
                listing.host_id, int(listing.is_superhost),
                listing.rating, listing.review_count,
            )).fetchone()
        return row["id"]

    # ------------------------------------------------------------------ #
    #  Calendar                                                            #
    # ------------------------------------------------------------------ #

    def upsert_calendar_days(self, days: list[CalendarDay]) -> None:
        if not days:
            return
        sql = """
        INSERT INTO calendar_days
            (listing_id, scrape_run_id, date, available, price_usd, min_nights)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(listing_id, date) DO UPDATE SET
            scrape_run_id = excluded.scrape_run_id,
            available     = excluded.available,
            price_usd     = excluded.price_usd,
            min_nights    = excluded.min_nights,
            scraped_at    = datetime('now')
        """
        with self.transaction():
            self._conn.executemany(sql, [
                (d.listing_id, d.scrape_run_id, d.date.isoformat(),
                 int(d.available), d.price_usd, d.min_nights)
                for d in days
            ])

    # ------------------------------------------------------------------ #
    #  Monthly metrics                                                     #
    # ------------------------------------------------------------------ #

    def upsert_monthly_metrics(self, m: MonthlyMetrics) -> None:
        sql = """
        INSERT INTO monthly_metrics
            (listing_id, year_month, nights_available, nights_booked,
             occupancy_rate, avg_daily_rate, revpar, est_revenue)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(listing_id, year_month) DO UPDATE SET
            nights_available = excluded.nights_available,
            nights_booked    = excluded.nights_booked,
            occupancy_rate   = excluded.occupancy_rate,
            avg_daily_rate   = excluded.avg_daily_rate,
            revpar           = excluded.revpar,
            est_revenue      = excluded.est_revenue,
            computed_at      = datetime('now')
        """
        with self.transaction():
            self._conn.execute(sql, (
                m.listing_id, m.year_month, m.nights_available,
                m.nights_booked, m.occupancy_rate, m.avg_daily_rate,
                m.revpar, m.est_revenue,
            ))

    # ------------------------------------------------------------------ #
    #  Queries                                                             #
    # ------------------------------------------------------------------ #

    def get_market_summary(self, city: str, year_month: str = None):
        ym_filter = f"AND m.year_month = '{year_month}'" if year_month else ""
        sql = f"""
        SELECT
            l.platform,
            COUNT(DISTINCT l.id)         AS listings,
            AVG(m.occupancy_rate) * 100  AS avg_occ_pct,
            AVG(m.avg_daily_rate)        AS avg_adr,
            AVG(m.revpar)                AS avg_revpar,
            SUM(m.est_revenue)           AS total_est_revenue
        FROM listings l
        JOIN monthly_metrics m ON m.listing_id = l.id
        WHERE l.city = ? {ym_filter}
        GROUP BY l.platform
        ORDER BY l.platform
        """
        return self._conn.execute(sql, (city,)).fetchall()

    def get_listings_with_metrics(self, city: str, platform: str = None,
                                   year_month: str = None):
        pf = f"AND l.platform = '{platform}'" if platform and platform != "all" else ""
        mf = f"AND m.year_month = '{year_month}'" if year_month else ""
        sql = f"""
        SELECT
            l.platform, l.external_id, l.source_url, l.title, l.city,
            l.neighborhood, l.latitude, l.longitude, l.property_type,
            l.bedrooms, l.bathrooms, l.max_guests, l.rating, l.review_count,
            l.is_superhost,
            m.year_month, m.nights_available, m.nights_booked,
            m.occupancy_rate, m.avg_daily_rate, m.revpar, m.est_revenue,
            sr.started_at AS scraped_at
        FROM listings l
        LEFT JOIN monthly_metrics m ON m.listing_id = l.id
        LEFT JOIN scrape_runs sr ON sr.id = l.scrape_run_id
        WHERE l.city = ? {pf} {mf}
        ORDER BY l.platform, l.external_id, m.year_month
        """
        return self._conn.execute(sql, (city,)).fetchall()

    # ------------------------------------------------------------------ #
    #  Private                                                             #
    # ------------------------------------------------------------------ #

    def _run_migrations(self) -> None:
        migrations_path = Path(__file__).parent.parent / "migrations"
        for sql_file in sorted(migrations_path.glob("*.sql")):
            self._conn.executescript(sql_file.read_text())
        self._conn.commit()
