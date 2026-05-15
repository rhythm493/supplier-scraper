from __future__ import annotations

import re

from bs4 import BeautifulSoup

from scraper.validators import normalize_country, normalize_email, normalize_phone

_PERSON_PATTERNS = [
    re.compile(r"contact\s*(?:person|us|info|sales)?[\s:]+\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b", re.I),
    re.compile(r"sales\s*(?:contact|manager|director)?[\s:]+\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b", re.I),
    re.compile(r"managing\s*(?:director|partner)?[\s:]+\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b", re.I),
    re.compile(
        r"(?:ceo|president|director|manager|founder|owner|coordinator)[\s:]+\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b",
        re.I,
    ),
]

_ROLE_PATTERNS = [
    re.compile(
        r"\b(CEO|President|Managing Director|Sales Manager|Marketing Manager|Operations Manager|General Manager|Technical Manager|Production Manager|Quality Manager|Director|Founder|Owner|Coordinator|Supervisor|Executive)\b",
        re.I,
    ),
]

_NAME_REGEX = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b")


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


def extract_contact_person(html_content: str) -> tuple[str, str]:
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        text_content = soup.get_text()

        author_tag = soup.find("meta", attrs={"name": "author"})
        if hasattr(author_tag, "get"):
            content = author_tag.get("content")  # type: ignore[union-attr]
            if content and isinstance(content, str):
                return content.strip(), "Not Found"

        lines = [ln.strip() for ln in text_content.split("\n") if ln.strip()]

        for pattern in _PERSON_PATTERNS:
            for line in lines:
                match = pattern.search(line)
                if match:
                    name = match.group(1).strip()
                    if 4 < len(name) < 60 and " " in name:
                        role = _extract_role(line, name) or "Not Found"
                        return name, role

        for pattern in _ROLE_PATTERNS:
            for line in lines:
                role_match = pattern.search(line)
                if role_match:
                    role = role_match.group(1)
                    names_in_line = _NAME_REGEX.findall(line)
                    for name in names_in_line:
                        if 4 < len(name) < 60 and " " in name:
                            return name, role

        return "Not Found", "Not Found"
    except Exception:
        return "Not Found", "Not Found"


def _extract_role(line: str, name: str) -> str | None:
    cleaned = line.replace(name, "").strip().lstrip(":-—–,;").strip()
    for pattern in _ROLE_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            return match.group(1)
    return None
