from __future__ import annotations

import logging
import random
import re
import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from scraper.extractors import (
    extract_city,
    extract_company_name,
    extract_contact_person,
    extract_country,
    extract_email,
    extract_phone,
    extract_products,
    extract_state,
)
from scraper.types import ContactInfo

if TYPE_CHECKING:
    from patchright.sync_api import Page

    from scraper.config import Config

logger = logging.getLogger(__name__)


def extract_company_info(page: Page, url: str, name: str, config: Config) -> ContactInfo | None:
    if not _is_valid_url(url):
        logger.info("Skipping invalid URL: %s", url)
        return None

    try:
        logger.info("Visiting: %s", url)
        html = None
        try:
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(random.uniform(0.5, 1.5))
            html = page.content()
        except Exception as se:
            logger.warning("Playwright failed on %s — trying requests fallback: %s", url, se)
            try:
                resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}, verify=False)
                if resp.status_code == 200:
                    html = resp.text
            except Exception as re:
                logger.warning("Requests fallback also failed for %s: %s", url, re)

        if html is None:
            logger.error("Failed to fetch %s via both Playwright and requests", url)
            return None

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        company_name = extract_company_name(html, url, name)
        contact = ContactInfo(
            email="Not Found",
            phone="Not Found",
            country="Not Found",
            state="Not Found",
            city="Not Found",
            company_name=company_name,
        )
        logger.info("Company name: %s", company_name)

        contact.email = extract_email(html) or "Not Found"
        contact.phone = extract_phone(html, config.phone_patterns, config.phone_prefixes) or "Not Found"
        contact.country = extract_country(html, config.countries, config.country_keywords) or "Not Found"
        contact.city = extract_city(html) or "Not Found"
        contact.state = extract_state(html) or "Not Found"

        person, role = extract_contact_person(html)
        if person != "Not Found":
            contact.contact_person = person
            contact.position = role

        if contact.email == "Not Found" or contact.phone == "Not Found":
            contact_url = _find_page(page, url, config.contact_keywords)
            if contact_url:
                logger.info("Checking contact page: %s", contact_url)
                info = _scrape_page(page, contact_url, config, contact)
                if info:
                    contact = info

        if contact.email == "Not Found" or contact.phone == "Not Found":
            about_keywords = ["about", "company", "our story", "profile"]
            about_url = _find_page(page, url, about_keywords)
            if about_url:
                logger.info("Checking about page: %s", about_url)
                info = _scrape_page(page, about_url, config, contact)
                if info:
                    contact = info

        if not _check_relevance(text, config.product_categories):
            logger.info("Not relevant to target categories: %s", url)
            return None

        if _is_ecommerce(soup, config.ecommerce_indicators):
            logger.info("E-commerce site, skipping: %s", url)
            return None

        products = extract_products(html, config.product_categories)
        if products:
            contact.products = ", ".join(products)
            logger.info("Found products: %s", contact.products)

        return contact

    except Exception:
        logger.exception("Failed to extract info from %s", url)
        return None


def _scrape_page(page: Page, page_url: str, config: Config, existing: ContactInfo) -> ContactInfo | None:
    try:
        html = None
        try:
            page.goto(page_url, wait_until="domcontentloaded")
            time.sleep(random.uniform(0.8, 2))
            html = page.content()
        except Exception as se:
            logger.warning("Playwright failed on contact page %s — trying requests fallback: %s", page_url, se)
            try:
                resp = requests.get(page_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}, verify=False)
                if resp.status_code == 200:
                    html = resp.text
            except Exception as re:
                logger.warning("Requests fallback also failed for %s: %s", page_url, re)

        if html is None:
            return None

        contact = ContactInfo(
            email=existing.email,
            phone=existing.phone,
            country=existing.country,
            state=existing.state,
            city=existing.city,
            company_name=existing.company_name,
            contact_person=existing.contact_person,
            position=existing.position,
        )

        if contact.email == "Not Found":
            email = extract_email(html)
            if email:
                contact.email = email

        if contact.phone == "Not Found":
            phone = extract_phone(html, config.phone_patterns, config.phone_prefixes)
            if phone:
                contact.phone = phone

        if contact.country == "Not Found":
            country = extract_country(html, config.countries, config.country_keywords)
            if country:
                contact.country = country

        if contact.city == "Not Found":
            city = extract_city(html)
            if city:
                contact.city = city

        if contact.state == "Not Found":
            state = extract_state(html)
            if state:
                contact.state = state

        if contact.contact_person == "Not Found":
            person, role = extract_contact_person(html)
            if person != "Not Found":
                contact.contact_person = person
                contact.position = role

        return contact

    except Exception:
        logger.exception("Failed to scrape page: %s", page_url)
        return None


_SOCIAL_DOMAINS = {"facebook.com", "twitter.com", "x.com", "linkedin.com", "instagram.com"}


def _is_valid_url(url: str) -> bool:
    if not url.startswith(("http://", "https://")):
        return False
    try:
        parsed = urlparse(url)
        if parsed.hostname:
            parts = parsed.hostname.split(".")
            if len(parts) >= 2 and ".".join(parts[-2:]) in _SOCIAL_DOMAINS:
                return False
    except Exception:
        return False
    return True


def _find_page(page: Page, base_url: str, keywords: list[str]) -> str | None:
    try:
        patterns = [
            f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}')]"
            for kw in keywords
        ] + [
            f"//a[contains(@href, '{kw.lower().replace(' ', '')}') or contains(@href, '{kw.lower().replace(' ', '-')}')]"
            for kw in keywords
        ]

        for pat in patterns:
            elements = page.locator(pat).element_handles()
            if elements:
                href = elements[0].get_attribute("href")
                if href and _is_valid_url(href):
                    return href

        domain_match = re.match(r"(https?://[^/]+)", base_url)
        if not domain_match:
            return None
        domain = domain_match.group(1)

        for kw in keywords:
            slug = kw.lower().replace(" ", "-").replace("_", "-")
            candidate = f"{domain}/{slug}"
            try:
                resp = requests.head(candidate, timeout=5, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
                if resp.ok:
                    return candidate
            except requests.RequestException:
                continue

        return None

    except Exception:
        logger.exception("Error finding page")
        return None


def _check_relevance(text: str, categories: list[str]) -> bool:
    text_lower = text.lower()
    score = 0
    for cat in categories:
        if cat.lower() in text_lower:
            score += 1

    manu_terms = ["manufacturer", "manufacturing", "production", "factory", "made in"]
    for term in manu_terms:
        if term in text_lower:
            score += 1

    return score >= 2


def _is_ecommerce(soup: BeautifulSoup, indicators: list[str]) -> bool:
    text = soup.get_text().lower()

    ecom_text_score = sum(1 for ind in indicators if ind.lower() in text)

    cart = soup.find_all(["a", "button", "div"], text=re.compile(r"cart|checkout|add to|buy now", re.IGNORECASE))
    grid = soup.select("div.product-grid, div.item-grid, div.catalog, ul.product-grid, ul.item-grid, ul.catalog")

    structural_count = len(cart) + len(grid)
    return ecom_text_score >= 6 and structural_count >= 3
