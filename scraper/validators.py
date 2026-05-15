from __future__ import annotations

import re
from urllib.parse import urlparse

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp"}


def normalize_email(email: str) -> str | None:
    email = email.strip().lower()
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return None
    exclude_domains = {"example.com", "yourdomain.com", "domain.com", "test.com", "localhost"}
    domain = email.split("@", 1)[1] if "@" in email else ""
    if domain in exclude_domains:
        return None
    domain_part = "@" + domain
    for ext in _IMAGE_EXTENSIONS:
        if domain_part.endswith(ext):
            return None
    if "@2x." in domain_part or "@3x." in domain_part:
        return None
    return email


def normalize_phone(phone: str, prefixes: list[str]) -> str | None:
    cleaned = re.sub(r"[\s\-\(\)\.]", "", phone)
    if not cleaned or not cleaned[-1].isdigit():
        return None

    digits = re.sub(r"\D", "", cleaned)
    if len(digits) < 7 or len(digits) > 14:
        return None

    if re.match(r"^(\d)\1{5,}$", digits):
        return None

    stripped_prefixes = sorted(
        [(re.sub(r"\D", "", p), p) for p in prefixes if re.sub(r"\D", "", p)],
        key=lambda x: len(x[0]),
        reverse=True,
    )
    for stripped, original in stripped_prefixes:
        if cleaned.startswith(stripped):
            rest = cleaned[len(stripped) :]
            return f"{original} {rest}" if rest else original

    if len(digits) >= 9:
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
