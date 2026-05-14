from __future__ import annotations

import re

from bs4 import BeautifulSoup

from scraper.validators import normalize_country, normalize_email, normalize_phone


def extract_email(html_content: str) -> str | None:
    try:
        pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        emails = re.findall(pattern, html_content)

        for email in emails:
            normalized = normalize_email(email)
            if normalized:
                if normalized.split("@")[0].startswith(("contact", "info", "enquiry", "sales", "support")):
                    return normalized
                return normalized

        return None
    except Exception:
        return None


def extract_phone(html_content: str, phone_patterns: list[str], prefixes: list[str]) -> str | None:
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        text_content = soup.get_text()

        for pattern in phone_patterns:
            matches = re.findall(pattern, text_content)
            if not matches:
                continue

            phone = matches[0].strip()
            normalized = normalize_phone(phone, prefixes)
            if normalized:
                return normalized

        return None
    except Exception:
        return None


def extract_country(
    html_content: str,
    countries: list[str],
    country_keywords: list[str],
) -> str | None:
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        text_content = soup.get_text()

        address_containers = soup.find_all(
            ["p", "div", "span"],
            text=re.compile("|".join(re.escape(kw.split(":")[0]) for kw in country_keywords), re.IGNORECASE),
        )

        search_texts: list[str] = [text_content]
        for container in address_containers:
            parent = container.find_parent(["div", "section", "address"])
            if parent:
                search_texts.append(parent.get_text())

        for search_text in search_texts:
            for country in countries:
                if re.search(r"\b" + re.escape(country) + r"\b", search_text, re.IGNORECASE):
                    normalized = normalize_country(country, countries)
                    if normalized:
                        return normalized

        return None
    except Exception:
        return None


def extract_products(html_content: str, categories: list[str]) -> list[str]:
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        text_content = soup.get_text().lower()

        found: list[str] = []
        for category in categories:
            if category.lower() in text_content and category not in found:
                found.append(category)

        return found
    except Exception:
        return []
