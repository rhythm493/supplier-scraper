from __future__ import annotations

import logging
import random
import re
import time
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from scraper.extractors import extract_contact_person, extract_country, extract_email, extract_phone, extract_products
from scraper.types import ContactInfo

if TYPE_CHECKING:
    from selenium.webdriver import Chrome

    from scraper.config import Config

logger = logging.getLogger(__name__)


def extract_company_info(driver: Chrome, url: str, name: str, config: Config) -> ContactInfo | None:
    contact = ContactInfo(
        email="Not Found", phone="Not Found", country="Not Found", state="Not Found", city="Not Found"
    )

    try:
        logger.info("Visiting: %s", url)
        driver.get(url)
        time.sleep(random.uniform(2, 4))

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        contact.email = extract_email(html) or "Not Found"
        contact.phone = extract_phone(html, config.phone_patterns, config.phone_prefixes) or "Not Found"
        contact.country = extract_country(html, config.countries, config.country_keywords) or "Not Found"

        person, role = extract_contact_person(html)
        if person != "Not Found":
            contact.contact_person = person
            contact.position = role

        if contact.email == "Not Found" or contact.phone == "Not Found":
            contact_url = _find_page(driver, url, config.contact_keywords)
            if contact_url:
                logger.info("Checking contact page: %s", contact_url)
                info = _scrape_page(driver, contact_url, config, contact)
                if info:
                    contact = info

        if contact.email == "Not Found" or contact.phone == "Not Found":
            about_keywords = ["about", "company", "our story", "profile"]
            about_url = _find_page(driver, url, about_keywords)
            if about_url:
                logger.info("Checking about page: %s", about_url)
                info = _scrape_page(driver, about_url, config, contact)
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


def _scrape_page(driver: Chrome, page_url: str, config: Config, existing: ContactInfo) -> ContactInfo | None:
    try:
        driver.get(page_url)
        time.sleep(random.uniform(1.5, 3))
        html = driver.page_source

        contact = ContactInfo(
            email=existing.email,
            phone=existing.phone,
            country=existing.country,
            state=existing.state,
            city=existing.city,
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

        if contact.contact_person == "Not Found":
            person, role = extract_contact_person(html)
            if person != "Not Found":
                contact.contact_person = person
                contact.position = role

        return contact

    except Exception:
        logger.exception("Failed to scrape page: %s", page_url)
        return None


def _find_page(driver: Chrome, base_url: str, keywords: list[str]) -> str | None:
    try:
        patterns = [
            f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}')]"
            for kw in keywords
        ] + [
            f"//a[contains(@href, '{kw.lower().replace(' ', '')}') or contains(@href, '{kw.lower().replace(' ', '-')}')]"
            for kw in keywords
        ]

        for pat in patterns:
            elements = driver.find_elements("xpath", pat)
            if elements:
                href = elements[0].get_attribute("href")
                if href:
                    return href

        domain_match = re.match(r"(https?://[^/]+)", base_url)
        if not domain_match:
            return None
        domain = domain_match.group(1)

        for kw in keywords:
            slug = kw.lower().replace(" ", "-").replace("_", "-")
            candidate = f"{domain}/{slug}"
            try:
                driver.execute_script(
                    f"var xhr = new XMLHttpRequest(); xhr.open('HEAD', '{candidate}', false); xhr.send(null);"
                )
                return candidate
            except Exception:
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
    grid = soup.find_all(["div", "ul"], class_=re.compile(r"product-grid|item-grid|catalog", re.IGNORECASE))

    structural_count = len(cart) + len(grid)
    return ecom_text_score >= 6 and structural_count >= 3
