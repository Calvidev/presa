"""
STR Agent CLI — AirDNA-like short-term rental data scraper.

Commands:
  scrape        Scrape listings for a city (Airbnb / Booking / VRBO / all)
  export        Export scraped data to CSV or JSON
  show-metrics  Print aggregate market metrics for a city
  runs          List recent scrape runs
"""
from __future__ import annotations
import asyncio
import datetime
import logging
from typing import Optional

import click

from .config import get_settings, Settings
from .database import Database
from .exporter import export_csv, export_json
from .http.browser import BrowserPool
from .http.curl_client import CurlClient
from .http.proxy import ProxyPool
from .metrics import compute_monthly_metrics
from .scrapers.airbnb import AirbnbScraper
from .scrapers.booking import BookingScraper
from .scrapers.vrbo import VrboScraper
from .utils.rate_limiter import TokenBucketLimiter

PLATFORMS = ["airbnb", "booking", "vrbo", "all"]


@click.group()
@click.option("--db",        default="str_data.db", help="SQLite database path")
@click.option("--log-level", default="INFO",         help="Logging verbosity")
@click.pass_context
def cli(ctx, db: str, log_level: str) -> None:
    """STR Agent — short-term rental data scraper."""
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    settings = get_settings()
    settings.db_path = db  # type: ignore[assignment]
    from pathlib import Path
    settings.db_path = Path(db)
    ctx.ensure_object(dict)
    ctx.obj["settings"] = settings


# ------------------------------------------------------------------ #
#  scrape                                                              #
# ------------------------------------------------------------------ #

@cli.command()
@click.argument("city")
@click.option("--platform",      type=click.Choice(PLATFORMS), default="all",
              help="Platform to scrape (default: all)")
@click.option("--check-in",      default=None,
              help="Check-in date YYYY-MM-DD (default: today)")
@click.option("--check-out",     default=None,
              help="Check-out date YYYY-MM-DD (default: today + 30 days)")
@click.option("--max-listings",  default=200, type=int,
              help="Max listings per platform (default: 200)")
@click.pass_context
def scrape(ctx, city: str, platform: str, check_in: Optional[str],
           check_out: Optional[str], max_listings: int) -> None:
    """Scrape STR listings for CITY and store results in the database."""
    settings = ctx.obj["settings"]
    settings.max_listings = max_listings

    today     = datetime.date.today()
    check_in  = check_in  or today.isoformat()
    check_out = check_out or (today + datetime.timedelta(days=30)).isoformat()

    asyncio.run(_run_scrape(settings, city, platform, check_in, check_out))


async def _run_scrape(settings: Settings, city: str, platform: str,
                       check_in: str, check_out: str) -> None:
    db = Database(settings.db_path)
    db.connect()

    proxy_pool = (
        ProxyPool.from_single(
            settings.proxy.host, settings.proxy.port,
            settings.proxy.username, settings.proxy.password,
        )
        if settings.proxy.enabled else ProxyPool()
    )
    limiter      = TokenBucketLimiter(settings.rate_limit)
    browser_pool = BrowserPool(settings, proxy_pool)
    await browser_pool.start()

    to_run = ["airbnb", "booking", "vrbo"] if platform == "all" else [platform]

    try:
        for plat in to_run:
            run_id = db.start_scrape_run(plat, city)
            found, saved, error_msg = 0, 0, None
            click.echo(f"\n[{plat}] Scraping '{city}' ({check_in} → {check_out}) …")

            try:
                scraper = _build_scraper(plat, settings, limiter,
                                          browser_pool, proxy_pool)
                async for result in scraper.scrape_city(city, check_in, check_out):
                    found += 1
                    listing_id = db.upsert_listing(result.listing, run_id)
                    for day in result.calendar_days:
                        day.listing_id    = listing_id
                        day.scrape_run_id = run_id
                    db.upsert_calendar_days(result.calendar_days)

                    metrics = compute_monthly_metrics(listing_id, result.calendar_days)
                    for m in metrics:
                        db.upsert_monthly_metrics(m)

                    saved += 1
                    label = result.listing.title or result.listing.external_id
                    click.echo(f"  ✓ [{plat}] {label}")

            except Exception as e:
                error_msg = str(e)
                logging.getLogger(__name__).exception(
                    "Scrape failed for %s/%s", plat, city
                )

            db.finish_scrape_run(run_id, found, saved, error_msg)
            status = "FAILED" if error_msg else "OK"
            click.echo(f"[{plat}] {status}: {saved}/{found} listings saved "
                       f"(run #{run_id})")
    finally:
        await browser_pool.stop()
        db.close()


def _build_scraper(platform: str, settings: Settings,
                    limiter: TokenBucketLimiter,
                    browser_pool: BrowserPool,
                    proxy_pool: ProxyPool):
    if platform == "airbnb":
        return AirbnbScraper(settings, limiter, browser_pool)
    elif platform == "vrbo":
        return VrboScraper(settings, limiter, browser_pool)
    elif platform == "booking":
        curl = CurlClient(settings, proxy_pool)
        return BookingScraper(settings, limiter, curl)
    raise ValueError(f"Unknown platform: {platform}")


# ------------------------------------------------------------------ #
#  export                                                              #
# ------------------------------------------------------------------ #

@cli.command()
@click.argument("city")
@click.option("--platform",   type=click.Choice(PLATFORMS), default="all")
@click.option("--format",     "fmt", type=click.Choice(["csv", "json"]),
              default="csv")
@click.option("--output",     default=None, help="Output file path")
@click.option("--year-month", default=None, help="Filter to YYYY-MM (optional)")
@click.pass_context
def export(ctx, city: str, platform: str, fmt: str,
           output: Optional[str], year_month: Optional[str]) -> None:
    """Export scraped data for CITY to CSV or JSON."""
    settings = ctx.obj["settings"]
    db       = Database(settings.db_path)
    db.connect()

    safe_city = city.replace(" ", "_").replace(",", "")
    output    = output or f"{safe_city}_{platform}.{fmt}"
    if fmt == "csv":
        export_csv(db, city, platform, output, year_month)
    else:
        export_json(db, city, platform, output, year_month)
    click.echo(f"Exported → {output}")
    db.close()


# ------------------------------------------------------------------ #
#  show-metrics                                                        #
# ------------------------------------------------------------------ #

@cli.command("show-metrics")
@click.argument("city")
@click.option("--year-month", default=None,
              help="Filter to YYYY-MM (default: all months)")
@click.pass_context
def show_metrics(ctx, city: str, year_month: Optional[str]) -> None:
    """Print aggregate market metrics (occupancy, ADR, RevPAR) for CITY."""
    settings = ctx.obj["settings"]
    db       = Database(settings.db_path)
    db.connect()

    rows = db.get_market_summary(city, year_month)
    label = f"{city}" + (f" ({year_month})" if year_month else "")
    click.echo(f"\n{'='*60}")
    click.echo(f"  Market Summary: {label}")
    click.echo(f"{'='*60}")
    if not rows:
        click.echo("  No data found. Run `str-agent scrape` first.")
    else:
        click.echo(f"  {'Platform':<12} {'Listings':>8} {'Occ%':>8} "
                   f"{'ADR':>8} {'RevPAR':>8} {'Est.Revenue':>14}")
        click.echo(f"  {'-'*64}")
        for row in rows:
            click.echo(
                f"  {row['platform']:<12} "
                f"{row['listings']:>8} "
                f"{(row['avg_occ_pct'] or 0):>7.1f}% "
                f"${(row['avg_adr'] or 0):>7.0f} "
                f"${(row['avg_revpar'] or 0):>7.0f} "
                f"${(row['total_est_revenue'] or 0):>13,.0f}"
            )
    click.echo()
    db.close()


# ------------------------------------------------------------------ #
#  runs                                                                #
# ------------------------------------------------------------------ #

@cli.command()
@click.option("--limit", default=20, type=int, help="Number of recent runs")
@click.pass_context
def runs(ctx, limit: int) -> None:
    """List recent scrape runs."""
    settings = ctx.obj["settings"]
    db       = Database(settings.db_path)
    db.connect()

    rows = db._conn.execute(
        "SELECT id, platform, city, status, listings_found, listings_saved, "
        "started_at, finished_at FROM scrape_runs "
        "ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()

    click.echo(f"\n{'ID':>4}  {'Platform':<10} {'City':<20} {'Status':<10} "
               f"{'Found':>6} {'Saved':>6}  Started")
    click.echo("-" * 75)
    for r in rows:
        click.echo(
            f"{r['id']:>4}  {r['platform']:<10} {r['city']:<20} "
            f"{r['status']:<10} {r['listings_found']:>6} {r['listings_saved']:>6}"
            f"  {r['started_at']}"
        )
    db.close()
