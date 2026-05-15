from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
]


@dataclass(slots=True)
class Config:
    search_queries: list[str] = field(default_factory=list)
    excluded_sites: list[str] = field(default_factory=list)

    max_search_attempts: int = 5
    max_search_pages: int = 10
    page_load_timeout: int = 25
    screenshots: bool = False
    user_agents: list[str] = field(default_factory=lambda: list(DEFAULT_USER_AGENTS))

    contact_keywords: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    country_keywords: list[str] = field(default_factory=list)
    phone_prefixes: list[str] = field(default_factory=list)
    phone_patterns: list[str] = field(default_factory=list)
    product_categories: list[str] = field(default_factory=list)
    ecommerce_indicators: list[str] = field(default_factory=list)

    output_filename: str = "suppliers.xlsx"
    log_filename: str = "scraper.log"

    def search_config_hash(self) -> str:
        parts = {
            "search_queries": sorted(self.search_queries),
            "max_search_pages": self.max_search_pages,
            "max_search_attempts": self.max_search_attempts,
            "excluded_sites": sorted(self.excluded_sites),
        }
        raw = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def cache_dir(self) -> str:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        name = os.path.splitext(os.path.basename(self.output_filename))[0]
        return os.path.join(base, "cache", name)
