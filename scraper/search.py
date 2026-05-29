from __future__ import annotations

import json
import logging
import os
import random
import re
import time
import urllib.parse
from collections.abc import Callable
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from scraper.types import SearchResult

if TYPE_CHECKING:
    from patchright.sync_api import Page

    from scraper.config import Config

logger = logging.getLogger(__name__)

_CAPTCHA_TIMEOUT = 300

_CAPTCHA_INDICATORS = [
    "captcha",
    "unusual traffic",
    "verify you're human",
    "enter the characters",
    "i'm not a robot",
    "are you a robot",
    "sorry, please try again later",
    "our systems have detected unusual traffic",
    "this page could not be loaded automatically",
]


def google_search(page: Page, query: str, config: Config) -> dict[str, SearchResult]:
    all_results: dict[str, SearchResult] = {}

    for attempt in range(config.max_search_attempts):
        try:
            logger.info("Search attempt %d/%d: %s", attempt + 1, config.max_search_attempts, query)

            search_url = _build_search_url(query, attempt)
            _random_delay(1, 3)

            if attempt == 0:
                page.context.clear_cookies()

            logger.info("Navigating to: %s", search_url)
            page.goto(search_url, wait_until="domcontentloaded")
            _random_delay(2, 4)

            _wait_for_captcha(page, f"search-{attempt + 1}")

            if search_url == "https://www.google.com":
                _handle_consent_popup(page)
                _type_and_search(page, query)
                _wait_for_captcha(page, f"search-{attempt + 1}-results")
                continue

            _handle_consent_popup(page)
            _human_scroll(page)

            for page_num in range(1, config.max_search_pages + 1):
                _wait_for_captcha(page, f"search-{attempt + 1}-page-{page_num}")

                if config.screenshots:
                    _save_screenshot(page, query, attempt, page_num)

                page_results = _extract_search_results(page, config.excluded_sites)
                if page_results:
                    logger.info("Found %d results on page %d", len(page_results), page_num)
                    for title, result in page_results.items():
                        if title not in all_results:
                            all_results[title] = result
                else:
                    logger.info("No results on page %d", page_num)

                if page_num < config.max_search_pages:
                    success = _navigate_next_page(page)
                    if not success:
                        logger.info("No more pages available")
                        break

            if all_results:
                logger.info("Found %d unique results on attempt %d", len(all_results), attempt + 1)
                break

        except Exception:
            logger.exception("Search attempt %d failed", attempt + 1)

    return all_results


def detect_captcha(page: Page) -> bool:
    try:
        page_text = page.content().lower()

        for indicator in _CAPTCHA_INDICATORS:
            if indicator in page_text:
                logger.warning("CAPTCHA text indicator found: %r", indicator)
                return True

        iframes = page.locator("iframe").element_handles()
        for iframe in iframes:
            src = (iframe.get_attribute("src") or "").lower()
            if "recaptcha" in src or "captcha" in src:
                logger.warning("CAPTCHA iframe found: %s", src[:100])
                return True

        captcha_elements = page.locator(
            "//*[contains(@class, 'g-recaptcha') or contains(@class, 'captcha') or contains(@id, 'captcha')]"
        ).element_handles()
        if captcha_elements:
            logger.warning("CAPTCHA element found on page")
            return True

    except Exception:
        pass

    return False


def wait_for_captcha(page: Page, label: str = "", on_captcha: Callable[[bool], None] | None = None) -> None:
    if not detect_captcha(page):
        return

    logger.warning("=" * 50)
    logger.warning("  CAPTCHA DETECTED%s!", f" ({label})" if label else "")
    logger.warning("  Please solve it manually in the browser window.")
    logger.warning("  The script will resume automatically once solved.")
    logger.warning("=" * 50)

    print("\n" + "!" * 50)
    print(f"  CAPTCHA DETECTED{' (' + label + ')' if label else ''}!")
    print("  -> Switch to the browser window and solve the captcha.")
    print("  -> The script will continue automatically when done.")
    print("!" * 50 + "\n")

    if on_captcha is not None:
        on_captcha(True)

    start = time.monotonic()
    try:
        while time.monotonic() - start < _CAPTCHA_TIMEOUT:
            time.sleep(3)
            if not detect_captcha(page):
                logger.info("CAPTCHA solved! Continuing...")
                print("\n  CAPTCHA solved. Resuming...\n")
                if on_captcha is not None:
                    on_captcha(False)
                return

        logger.error("CAPTCHA wait timed out after %d seconds", _CAPTCHA_TIMEOUT)
        raise TimeoutError(f"CAPTCHA not solved within {_CAPTCHA_TIMEOUT} seconds. Restart the script and try again.")
    except BaseException:
        if on_captcha is not None:
            on_captcha(False)
        raise


_wait_for_captcha = wait_for_captcha


def _query_slug(query: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", query).strip("-").lower()
    return slug[:80] if len(slug) > 80 else slug


def save_search_cache(cache_dir: str, query: str, results: dict[str, SearchResult], config_hash: str) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    slug = _query_slug(query)
    data = [{"title": r.title, "url": r.url} for r in results.values()]
    path = os.path.join(cache_dir, f"{slug}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    meta_path = os.path.join(cache_dir, "_meta.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
    else:
        meta = {"config_hash": config_hash, "queries": {}}
    meta["config_hash"] = config_hash
    meta["queries"][slug] = {"query": query, "count": len(results)}
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


def load_search_cache(cache_dir: str, config_hash: str, queries: list[str]) -> dict[str, SearchResult] | None:
    meta_path = os.path.join(cache_dir, "_meta.json")
    if not os.path.exists(meta_path):
        return None
    with open(meta_path) as f:
        meta = json.load(f)
    if meta.get("config_hash") != config_hash:
        return None
    all_results: dict[str, SearchResult] = {}
    for query in queries:
        slug = _query_slug(query)
        path = os.path.join(cache_dir, f"{slug}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
        for item in data:
            name = item["title"]
            if name not in all_results:
                all_results[name] = SearchResult(title=name, url=item["url"])
    return all_results if all_results else None


def _random_delay(min_s: float = 0.5, max_s: float = 2.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


def _human_scroll(page: Page, times: int = 2) -> None:
    for _ in range(times):
        delta = random.randint(100, 400)
        page.mouse.wheel(0, delta)
        time.sleep(random.uniform(0.3, 0.8))
    page.mouse.wheel(0, -random.randint(50, 150))
    time.sleep(0.2)
    _random_delay(0.2, 0.5)


_SEARCH_SUFFIXES = [
    "manufacturer",
    "company",
    "business",
    "firm",
    "supplier",
    "distributor",
    "exporter",
    "vendor",
    "dealer",
]


def _build_search_url(query: str, attempt: int) -> str:
    if attempt == 0:
        return f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
    if attempt == 1:
        return "https://www.google.com"
    suffix = _SEARCH_SUFFIXES[(attempt - 2) % len(_SEARCH_SUFFIXES)]
    modified = f"{query} {suffix}"
    return f"https://www.google.com/search?q={urllib.parse.quote_plus(modified)}"


def _handle_consent_popup(page: Page) -> None:
    try:
        page.locator(
            "//button[contains(., 'Accept') or contains(., 'Agree') or contains(., 'Accept all') or contains(., 'I agree') or contains(., 'Consent')]"
        ).click(timeout=5000)
        time.sleep(1.5)
    except Exception:
        pass


def _type_and_search(page: Page, query: str) -> None:
    try:
        search_box = page.locator('[name="q"]')
        search_box.wait_for(state="attached", timeout=5000)
        search_box.click()
        time.sleep(random.uniform(0.3, 0.8))
        search_box.press_sequentially(query, delay=random.randint(20, 80))
        _random_delay(0.3, 0.6)
        page.keyboard.press("Enter")
        _random_delay(2, 4)
    except Exception as e:
        logger.error("Error typing search query: %s", e)


def _save_screenshot(page: Page, query: str, attempt: int, page_num: int) -> None:
    try:
        safe_query = re.sub(r"[^a-zA-Z0-9]", "_", query)[:30]
        path = f"screenshot_{safe_query}_a{attempt}_p{page_num}.png"
        page.screenshot(path=path)
        logger.info("Screenshot saved: %s", path)
    except Exception as e:
        logger.error("Failed to save screenshot: %s", e)


def _extract_search_results(page: Page, excluded_sites: list[str] | None = None) -> dict[str, SearchResult]:
    results: dict[str, SearchResult] = {}

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    parsed_bs4 = soup.select("div.g, div.tF2Cxc, div.yuRUbf")
    if not parsed_bs4:
        parsed_bs4 = soup.select("div[data-hveid]")

    for result in parsed_bs4:
        try:
            link_elem = result if result.name == "a" else result.find("a")
            if not link_elem or not hasattr(link_elem, "get"):
                continue
            href_val = link_elem.get("href", "")
            if isinstance(href_val, list):
                continue
            if not href_val:
                continue

            title_elem = result.find("h3")
            title = (
                title_elem.get_text()
                if title_elem
                else str(link_elem.get_text() if hasattr(link_elem, "get_text") else "")
            )
            if not title:
                title = "Unknown"

            if _is_valid_result(href_val, excluded_sites):
                results[title] = SearchResult(title=title, url=href_val)
        except Exception:
            logger.exception("Error parsing search result")

    return results


def _is_valid_result(url: str, excluded_sites: list[str] | None = None) -> bool:
    try:
        google_domains = [
            "google.com",
            "google.co",
            "youtube.com",
            "accounts.google.com",
            "policies.google.com",
            "support.google.com",
            "maps.google.com",
        ]
        excluded = list(google_domains) + (excluded_sites or [])
        url_lower = url.lower()
        return not any(d in url_lower for d in excluded)
    except Exception:
        return False


def _navigate_next_page(page: Page) -> bool:
    try:
        selectors = [
            "//a[@id='pnnext']",
            "//span[text()='Next']/parent::a",
            "//a[contains(@class, 'pn')]",
            "//a[contains(text(), 'Next')]",
        ]

        for sel in selectors:
            try:
                with page.expect_navigation(timeout=5000):
                    page.locator(sel).click(timeout=4000)
                _random_delay(1, 2)
                return True
            except Exception:
                continue

        current_url = page.url
        if "start=" in current_url:
            match = re.search(r"start=(\d+)", current_url)
            if match:
                next_start = int(match.group(1)) + 10
                next_url = re.sub(r"start=\d+", f"start={next_start}", current_url)
            else:
                next_url = current_url + "&start=10"
        else:
            sep = "&" if "?" in current_url else "?"
            next_url = f"{current_url}{sep}start=10"
        page.goto(next_url, wait_until="domcontentloaded")
        _random_delay(2, 3)
        return True

    except Exception:
        logger.exception("Failed to navigate to next page")
        return False
