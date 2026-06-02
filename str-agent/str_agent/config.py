from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class ProxyConfig:
    enabled:  bool = False
    host:     str = ""
    port:     int = 0
    username: str = ""
    password: str = ""

    @property
    def url(self) -> str:
        return f"http://{self.username}:{self.password}@{self.host}:{self.port}"


@dataclass
class RateLimitConfig:
    requests_per_minute: int   = 12
    min_delay_s:         float = 2.0
    max_delay_s:         float = 5.0
    jitter_s:            float = 1.5


@dataclass
class Settings:
    db_path:       Path             = field(default_factory=lambda: Path("str_data.db"))
    proxy:         ProxyConfig      = field(default_factory=ProxyConfig)
    rate_limit:    RateLimitConfig  = field(default_factory=RateLimitConfig)
    headless:      bool             = True
    calendar_days: int              = 90
    max_listings:  int              = 200
    log_level:     str              = "INFO"


def get_settings() -> Settings:
    proxy = ProxyConfig(
        enabled  = os.getenv("PROXY_ENABLED", "false").lower() == "true",
        host     = os.getenv("PROXY_HOST", ""),
        port     = int(os.getenv("PROXY_PORT", "0") or "0"),
        username = os.getenv("PROXY_USER", ""),
        password = os.getenv("PROXY_PASS", ""),
    )
    return Settings(
        db_path       = Path(os.getenv("DB_PATH", "str_data.db")),
        proxy         = proxy,
        headless      = os.getenv("HEADLESS", "true").lower() == "true",
        calendar_days = int(os.getenv("CALENDAR_DAYS", "90")),
        max_listings  = int(os.getenv("MAX_LISTINGS", "200")),
        log_level     = os.getenv("LOG_LEVEL", "INFO"),
    )
