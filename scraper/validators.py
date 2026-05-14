from __future__ import annotations

import re
from urllib.parse import urlparse


def normalize_email(email: str) -> str | None:
    email = email.strip().lower()
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return None
    exclude_domains = {"example.com", "yourdomain.com", "domain.com", "test.com", "localhost"}
    domain = email.split("@", 1)[1] if "@" in email else ""
    if domain in exclude_domains:
        return None
    return email


def normalize_phone(phone: str, prefixes: list[str]) -> str | None:
    cleaned = re.sub(r"[\s\-\(\)\.]", "", phone)
    if not cleaned or not cleaned[-1].isdigit():
        return None
    for prefix in sorted(prefixes, key=len, reverse=True):
        stripped_prefix = re.sub(r"\D", "", prefix)
        if cleaned.startswith(stripped_prefix):
            return f"{prefix} {cleaned[len(stripped_prefix) :]}"
        if len(stripped_prefix) <= len(cleaned) and cleaned[: len(stripped_prefix)].isdigit():
            return cleaned
    return None


def normalize_country(country: str, whitelist: list[str]) -> str | None:
    country = country.strip().title()
    whitelist_lower = {c.lower(): c for c in whitelist}
    if country.lower() in whitelist_lower:
        return whitelist_lower[country.lower()]
    for canonical in whitelist:
        if len(country) > 3 and (
            canonical.lower().startswith(country.lower()) or country.lower().startswith(canonical.lower())
        ):
            return canonical
    return None


def extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = domain.removeprefix("www.").split(":")[0]
        return domain.lower()
    except Exception:
        return url.lower().strip("/")
