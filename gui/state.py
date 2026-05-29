from __future__ import annotations

import logging
import os
import threading
from typing import Any

import pandas as pd

from scraper import Config, run_scraper
from scraper import search as search_module

COLUMNS = [
    "Company Name",
    "Contact Person",
    "Position",
    "State",
    "City",
    "Country",
    "Phone Number",
    "Email",
    "Website",
    "Products",
]

DEFAULT_SEARCH_QUERIES = [
    "CSSD distributor in Africa",
    "Sterilization Reel distributor in Africa",
    "Sterilization pouches distributor in Africa",
    "Sterilization rolls supplier in Africa",
    "Doctor Gown distributor in Africa",
    "Sterile Gown supplier in Africa",
]

DEFAULT_EXCLUDED_SITES = [
    "alibaba.com",
    "amazon.",
    "ebay.",
    "aliexpress.com",
    "indiamart.com",
    "tradeindia.com",
    "made-in-china.com",
    "walmart.com",
    "etsy.com",
    "linkedin.com",
    "wikipedia.org",
    "twitter.com",
    "instagram.com",
]

DEFAULT_PRODUCT_CATEGORIES = [
    "Sterilization and Infection Control",
    "infection control",
    "pouch",
    "indicator",
    "sterility",
    "biological indicator",
    "chemical indicator",
    "steam sterilizer",
    "EO sterilization",
    "plasma sterilization",
    "aseptic bags",
    "sterilization reels",
    "sterilization pouches",
    "sterility monitoring",
    "indicator strips",
    "autoclave tape",
    "surgeon gown",
    "isolation gown",
    "sterile gown",
    "sterilization",
    "sterile",
    "CSSD Consumables",
]

DEFAULT_COUNTRIES = [
    "Algeria",
    "Angola",
    "Botswana",
    "Egypt",
    "Ghana",
    "Kenya",
    "Morocco",
    "Namibia",
    "Nigeria",
    "South Africa",
    "Tanzania",
    "Tunisia",
    "Uganda",
    "Zambia",
    "Zimbabwe",
]

DEFAULT_COUNTRY_KEYWORDS = [
    "Country:",
    "Location:",
    "Address:",
    "Headquarters:",
    "Based in",
]

DEFAULT_CONTACT_KEYWORDS = [
    "contact",
    "about",
    "company",
    "directory",
    "support",
    "reach",
    "locations",
]

DEFAULT_PHONE_PREFIXES = [
    "+213",
    "+244",
    "+229",
    "+267",
    "+226",
    "+257",
    "+238",
    "+237",
    "+236",
    "+235",
    "+269",
    "+243",
    "+242",
    "+253",
    "+20",
    "+240",
    "+291",
    "+268",
    "+251",
    "+241",
    "+220",
    "+233",
    "+224",
    "+245",
    "+225",
    "+254",
    "+266",
    "+231",
    "+218",
    "+261",
    "+265",
    "+223",
    "+222",
    "+230",
    "+212",
    "+258",
    "+264",
    "+227",
    "+234",
    "+250",
    "+239",
    "+221",
    "+248",
    "+232",
    "+252",
    "+27",
    "+211",
    "+249",
    "+255",
    "+228",
    "+216",
    "+256",
    "+260",
    "+263",
]

DEFAULT_PHONE_PATTERNS = [
    r"\+?\d{1,3}[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}",
    r"\d{3}[\s-]?\d{3}[\s-]?\d{4}",
    r"\b\d{7,15}\b",
]

DEFAULT_ECOMMERCE_INDICATORS = [
    "add to cart",
    "buy now",
    "shopping cart",
    "checkout",
    "add to basket",
    "store",
    "shop",
    "purchase",
    "order",
    "price",
    "payment",
    "shipping",
    "delivery",
    "ecommerce",
]

scrape_state: dict[str, Any] = {
    "captcha": False,
    "df": pd.DataFrame(columns=COLUMNS),
    "log": [],
    "phase": "Ready",
    "done": False,
    "error": None,
    "output_path": None,
}

cancel_event: threading.Event | None = None


def build_config(
    search_queries: list[str],
    excluded_sites: list[str],
    product_categories: list[str],
    contact_keywords: list[str],
    countries: list[str],
    country_keywords: list[str],
    phone_prefixes: list[str],
    phone_patterns: list[str],
    ecommerce_indicators: list[str],
    output_filename: str,
    max_search_pages: int,
    max_search_attempts: int,
    page_load_timeout: int,
    screenshots: bool,
) -> Config:
    return Config(
        search_queries=search_queries,
        excluded_sites=excluded_sites,
        product_categories=product_categories,
        contact_keywords=contact_keywords,
        countries=countries,
        country_keywords=country_keywords,
        phone_prefixes=phone_prefixes,
        phone_patterns=phone_patterns,
        ecommerce_indicators=ecommerce_indicators,
        output_filename=output_filename,
        max_search_pages=max_search_pages,
        max_search_attempts=max_search_attempts,
        page_load_timeout=page_load_timeout,
        screenshots=screenshots,
    )


def patch_captcha_handler() -> None:
    original = search_module.wait_for_captcha

    def patched(page, label="", on_captcha=None):
        if not search_module.detect_captcha(page):
            return
        scrape_state["captcha"] = True
        scrape_state["log"].append(f"CAPTCHA detected ({label}) — solve in the browser window")
        original(page, label)
        scrape_state["captcha"] = False
        scrape_state["log"].append("CAPTCHA solved, resuming")

    search_module.wait_for_captcha = patched
    search_module._wait_for_captcha = patched


def start_scrape(config: Config) -> None:
    global cancel_event
    cancel_event = threading.Event()
    scrape_state["cancel_event"] = cancel_event
    t = threading.Thread(target=scraper_worker, args=(config,), daemon=True)
    t.start()


def scraper_worker(config: Config) -> None:
    root = logging.getLogger()

    class StateHandler(logging.Handler):
        def emit(self, record):
            msg = self.format(record)
            if len(scrape_state["log"]) > 500:
                scrape_state["log"] = scrape_state["log"][-250:]
            scrape_state["log"].append(msg)

    handler = StateHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
    root.addHandler(handler)

    try:

        def on_progress(df, completed, total, found, name):
            scrape_state["df"] = df
            scrape_state["phase"] = f"Phase 2: {name} ({completed}/{total})"

        scrape_state["phase"] = "Phase 1: Searching Google..."
        scrape_state["log"].append("Scraper started")
        df = run_scraper(config, on_progress=on_progress, cancel_event=cancel_event)

        scrape_state["df"] = df
        scrape_state["done"] = True
        output_path = os.path.abspath(config.output_filename)
        scrape_state["output_path"] = output_path
        scrape_state["log"].append(f"Done! {len(df)} companies -> {config.output_filename}")

        if cancel_event is not None and cancel_event.is_set():
            scrape_state["phase"] = f"Cancelled — {len(df)} companies collected"
        else:
            scrape_state["phase"] = f"Complete — {len(df)} companies"

    except Exception as e:
        if cancel_event is not None and cancel_event.is_set():
            scrape_state["log"].append("Cancelled by user")
            scrape_state["phase"] = "Cancelled"
        else:
            scrape_state["error"] = str(e)
            scrape_state["log"].append(f"Error: {e}")
            scrape_state["phase"] = f"Error: {e}"
    finally:
        root.removeHandler(handler)
