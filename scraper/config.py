from __future__ import annotations

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
