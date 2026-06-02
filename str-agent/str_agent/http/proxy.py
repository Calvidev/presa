from __future__ import annotations
import itertools
import logging
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class ProxyEntry:
    host:     str
    port:     int
    username: str
    password: str

    @property
    def playwright_url(self) -> str:
        return f"http://{self.username}:{self.password}@{self.host}:{self.port}"

    @property
    def curl_proxies(self) -> dict:
        return {"https": self.playwright_url, "http": self.playwright_url}


class ProxyPool:
    """Round-robin proxy rotation."""

    def __init__(self, proxies: list[ProxyEntry] = None):
        self._proxies = proxies or []
        self._cycle   = itertools.cycle(self._proxies) if self._proxies else None

    @classmethod
    def from_single(cls, host: str, port: int,
                    username: str, password: str) -> "ProxyPool":
        return cls([ProxyEntry(host, int(port), username, password)])

    @classmethod
    def from_file(cls, path: str) -> "ProxyPool":
        entries = []
        with open(path) as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) == 4:
                    entries.append(ProxyEntry(parts[0], int(parts[1]),
                                              parts[2], parts[3]))
        return cls(entries)

    def next(self) -> Optional[ProxyEntry]:
        return next(self._cycle) if self._cycle else None

    @property
    def is_empty(self) -> bool:
        return not self._proxies
