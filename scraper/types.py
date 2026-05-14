from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ContactInfo:
    email: str = "Not Found"
    phone: str = "Not Found"
    country: str = "Not Found"
    state: str = "Not Found"
    city: str = "Not Found"
    products: str = ""

    def is_contact_found(self) -> bool:
        return any(v != "Not Found" for v in (self.email, self.phone, self.country, self.state, self.city))


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
