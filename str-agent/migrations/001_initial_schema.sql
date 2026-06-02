CREATE TABLE IF NOT EXISTS scrape_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    platform        TEXT NOT NULL,
    city            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'running',   -- 'running' | 'completed' | 'failed'
    listings_found  INTEGER DEFAULT 0,
    listings_saved  INTEGER DEFAULT 0,
    error_msg       TEXT,
    started_at      TEXT DEFAULT (datetime('now')),
    finished_at     TEXT
);

CREATE TABLE IF NOT EXISTS listings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id     TEXT NOT NULL,
    platform        TEXT NOT NULL,          -- 'airbnb' | 'booking' | 'vrbo'
    scrape_run_id   INTEGER REFERENCES scrape_runs(id),
    source_url      TEXT,
    title           TEXT,
    city            TEXT NOT NULL,
    neighborhood    TEXT,
    latitude        REAL,
    longitude       REAL,
    property_type   TEXT,
    bedrooms        INTEGER,
    bathrooms       REAL,
    max_guests      INTEGER,
    amenities       TEXT,                   -- JSON array
    host_id         TEXT,
    is_superhost    INTEGER DEFAULT 0,
    rating          REAL,
    review_count    INTEGER,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(external_id, platform)
);

CREATE TABLE IF NOT EXISTS calendar_days (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id      INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    scrape_run_id   INTEGER REFERENCES scrape_runs(id),
    date            TEXT NOT NULL,          -- ISO-8601 YYYY-MM-DD
    available       INTEGER NOT NULL,       -- 1 = available, 0 = booked/blocked
    price_usd       REAL,
    min_nights      INTEGER,
    scraped_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(listing_id, date)
);

CREATE TABLE IF NOT EXISTS monthly_metrics (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id       INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    year_month       TEXT NOT NULL,         -- 'YYYY-MM'
    nights_available INTEGER,
    nights_booked    INTEGER,
    occupancy_rate   REAL,
    avg_daily_rate   REAL,
    revpar           REAL,
    est_revenue      REAL,
    computed_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(listing_id, year_month)
);

CREATE INDEX IF NOT EXISTS idx_listings_platform_city  ON listings(platform, city);
CREATE INDEX IF NOT EXISTS idx_listings_run            ON listings(scrape_run_id);
CREATE INDEX IF NOT EXISTS idx_calendar_listing_date   ON calendar_days(listing_id, date);
CREATE INDEX IF NOT EXISTS idx_calendar_run            ON calendar_days(scrape_run_id);
CREATE INDEX IF NOT EXISTS idx_metrics_listing_month   ON monthly_metrics(listing_id, year_month);
