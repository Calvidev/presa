from __future__ import annotations
import csv
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def export_csv(db, city: str, platform: str, output: str,
               year_month: str = None) -> None:
    rows = db.get_listings_with_metrics(city, platform, year_month)
    if not rows:
        log.warning("No data found for city=%s platform=%s", city, platform)
        return
    keys = rows[0].keys()
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])
    log.info("Exported %d rows to %s", len(rows), output)


def export_json(db, city: str, platform: str, output: str,
                year_month: str = None) -> None:
    rows = db.get_listings_with_metrics(city, platform, year_month)
    data = [dict(r) for r in rows]
    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    log.info("Exported %d records to %s", len(data), output)
