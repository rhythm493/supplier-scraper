from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from scraper.validators import normalize_country, normalize_email, normalize_phone

_SKIP_WORDS = {"And", "The", "For", "Of", "Our", "Us", "Today", "With", "Your", "This", "That", "From"}

_COMPANY_INDICATORS = {
    "Pvt",
    "Ltd",
    "GmbH",
    "Inc",
    "LLC",
    "Company",
    "Industries",
    "Corporation",
    "Corp",
    "Limited",
    "Healthcare",
    "Systems",
    "Solutions",
    "Supplies",
    "Services",
    "Products",
    "Product",
    "Equipment",
    "Technologies",
    "Enterprises",
    "Infrastructure",
    "Distribution",
    "Manufacturing",
    "Portfolio",
    "Business",
    "Network",
    "Supplier",
    "Suppliers",
    "Manufacturer", "Manufacturers",
    "Device",
    "Devices",
    "Instruments",
    "Health",
    "Estate",
    "Organization",
    "Platforms",
    "Meta",
}
_NON_PERSON_WORDS = {
    # Existing
    "User", "Admin", "Super", "Cookie", "Policy", "Select",
    "Page", "Home", "Returns", "Profile", "Overview",
    "Uniforms", "Accessories", "Login", "Register", "Sign",
    "Search", "Menu", "Navigation",
    "National", "International", "Regional", "Local",
    "Contact", "About", "Learn", "More", "Mail", "Eg", "Sample",
    "Loading", "Submit", "Please",
    # Geography / region — not person names
    "Africa", "African", "Saharan", "Southern", "Northern",
    "Eastern", "Western",
    "Arabia", "Bahrain", "Kuwait", "Saudi", "States", "United",
    # Street / address
    "Street", "Road", "Lane", "Drive", "Avenue", "Highway",
    "Way", "Park", "Office", "Village", "Township", "Ave",
    "Rd", "Coast", "Floor", "Ground", "Old", "Glen",
    "Postal", "Address", "Blvd",
    # Business / org
    "Institute", "Platform", "Portal", "Hub", "Centre", "Center",
    "Tel", "Data", "Management",
    "Training", "News", "Certificates",
    "Distributor", "Distributors", "Wholesaler", "Wholesalers",
    "Preventative", "Maintenance", "Program", "Programme", "Programmes",
    "Additional", "Information",
    "Industry", "Supply", "Department", "Authority",
    "Regulatory", "Policies", "Terms", "Use",
    "Site", "Request", "Forgery",
    "Seminars",
    # Products — not persons
    "Products", "Reels", "Reel", "Gown", "Gowns", "Pouch", "Pouches",
    "Bag", "Bags", "Wrap", "Wraps",
    "Portfolio", "Sterilization",
    "Wrapping", "Machine", "Over",
    "Animal", "Feed",
    "Better", "Care",
    "Cape", "Town",
    "Central", "Sterile",
    "Hellenic",
    # Commerce / UI labels
    "All", "Compare",
    "Feel", "Free", "Help",
    "Mobile", "No", "Need", "Name", "Full",
    "Near", "Support",
    "Instant", "Quote", "Shop", "Doe",
    "Message", "Related", "Substances", "Act",
    "Good", "Double", "Deluxe", "Practice",
    "Beauty",
    "Launch", "Sale",
    "Get", "Started", "Speak", "Self", "Sealable", "Dick",
    "Appliance", "Parts", "Arclight", "Diagnostics",
    "Developed", "Kids", "Toys",
    "Holy", "Grail", "Major", "General", "El",
    # Medical / infection control
    "Acquired", "Autoclave", "Autoclaves", "Consumables",
    "Control", "Hospital", "Infection", "Infections",
    "Laundry", "Market",
    "Soap", "Bar", "Packing", "Sterilizer", "Steam",
    "Instrument",
    "Mill", "Roller", "Rollers", "Stamping", "Table", "Top", "Triple", "Beaded",
    "Electronics", "Solar", "Charging", "Vertical",
    "Semi", "Automatic", "Operating", "Pan", "Track",
    "Ethylene", "Oxide", "Indicator", "Indicators", "Tapes",
    "Aluminium", "Casting",
    "Air", "Ring", "Aluminum", "Heat",
    "Ultrasonic", "Cleaner", "Washer", "Disinfector",
    "Layer", "Film", "Extrusion", "Line",
    "Pass", "Box", "Rack",
    # Company / business terms
    "Averda", "Based", "Black", "Economic", "Empowerment",
    "Cardiology", "Working", "Groups",
    "Largest",
    "Flat", "Rolls",
    "Pre",
    "Growthpoint",
    "Commercial", "Vehicles", "House",
    # Tech
    "Sitecore", "Engagement", "Analytics",
    # Product / equipment names
    "Printed", "Wrapper",
    "Seal", "Cover",
    "Sports", "Boating",
    "Trolley", "Scrub", "Station",
    "Stainless",
    "Inch", "Plane",
    "Medical", "Waste", "Shredder", "Integrated",
    "Medicine", "Books",
    "Master",
    "Boutique", "Automotive", "Car",
    "Doctor", "Blade",
    "High", "Spin",
    "Leading", "Organisations",
    "Gown", "Gowns",
    "Surgeon", "Surgical",
    "Disposable",
    "Protective",
    "Packaging",
    "Garden", "Dining",
    "Non", "Woven", "Mask", "Making",
    "Soft", "Mount",
    "Littmann", "Classic",
    "Kg", "Price",
    "Mechanical", "Shaft",
    "Secure", "Payments",
    "Approval", "Certificate",
    "Safety",
    "Service",
    # UI / common words
    "You", "Are",
}
_NOISE_WORDS = {
    "And",
    "The",
    "For",
    "Of",
    "Our",
    "Us",
    "Today",
    "With",
    "Your",
    "This",
    "That",
    "From",
    "South",
    "North",
    "East",
    "West",
    "Central",
    "Supreme",
    "Medical",
    "Surgical",
    "Africa",
    "Industrial",
    "Cardiovascular",
    "Numbers",
    "Media",
    "Share",
    "Rights",
    "Contact",
    "Products",
    "Product",
    "Portfolio",
    "Healthcare",
    "Systems",
    "Solutions",
    "Supplies",
    "Services",
    "Equipment",
    "Technologies",
    "Enterprises",
    "Distribution",
    "Manufacturing",
    "Business",
    "Network",
    "Cookie",
    "Policy",
    "Select",
    "Page",
    "Home",
    "Returns",
    "Profile",
    "Overview",
    "Uniforms",
    "Accessories",
    "Login",
    "Register",
    "Sign",
    "Search",
    "Menu",
    "Navigation",
    "National",
    "International",
    "Regional",
    "Local",
    "Pvt",
    "Ltd",
    "GmbH",
    "Inc",
    "LLC",
    "Company",
    "Industries",
    "Corporation",
    "Corp",
    "Limited",
}

_NAME_PATTERN = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b")

_PERSON_PATTERNS = [
    re.compile(r"(?i:contact\s*(?:person|us|info|sales))[\s:]+\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b"),
    re.compile(r"(?i:sales\s*(?:contact|manager|director))[\s:]+\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b"),
    re.compile(r"(?i:managing\s*(?:director|partner))[\s:]+\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b"),
    re.compile(
        r"(?i:ceo|president|director|manager|founder|owner|coordinator)[\s:]+\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b",
    ),
    re.compile(
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*[—–\-|]\s*"
        r"((?i:ceo|president|managing\s+director|director|manager|founder|owner|"
        r"coordinator|supervisor|executive|engineer|technician|specialist|analyst|"
        r"consultant|lead|head|chief|officer|partner|representative|assistant|associate)"
        r"(?:\s+(?:of|and|&|the|operations|sales|marketing|quality|production|technical|"
        r"general|finance|hr|rd|engineering|logistics|procurement|bd|customer|product|"
        r"design|manufacturing)){0,3})\b"
    ),
    re.compile(
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*\(((?i:ceo|president|director|manager|"
        r"founder|owner|coordinator|supervisor|executive))\s*\)"
    ),
]

_ROLE_PATTERNS = [
    re.compile(
        r"\b((?i:CEO|President|Managing Director|Sales Manager|Marketing Manager|"
        r"Operations Manager|General Manager|Technical Manager|Production Manager|"
        r"Quality Manager|Director|Founder|Owner|Coordinator|Supervisor|Executive|"
        r"C\.E\.O\.|M\.D\.|VP|Vice\s*President|Head\s+of|Lead|Chief|Officer|"
        r"Engineer|Technician|Specialist|Analyst|Consultant|Representative|"
        r"Assistant|Associate|Manager|Superintendent|Administrator))\b",
    ),
]
_ROLE_NORMALIZE = {
    "ceo": "CEO",
    "president": "President",
    "director": "Director",
    "founder": "Founder",
    "owner": "Owner",
    "coordinator": "Coordinator",
    "supervisor": "Supervisor",
    "executive": "Executive",
    "managing director": "Managing Director",
    "sales manager": "Sales Manager",
    "marketing manager": "Marketing Manager",
    "operations manager": "Operations Manager",
    "general manager": "General Manager",
    "technical manager": "Technical Manager",
    "production manager": "Production Manager",
    "quality manager": "Quality Manager",
    "c.e.o.": "CEO",
    "m.d.": "Managing Director",
    "vp": "VP",
    "vice president": "Vice President",
    "head of": "Head",
    "chief": "Chief",
    "officer": "Officer",
    "engineer": "Engineer",
    "technician": "Technician",
    "specialist": "Specialist",
    "analyst": "Analyst",
    "consultant": "Consultant",
    "representative": "Representative",
    "assistant": "Assistant",
    "associate": "Associate",
    "manager": "Manager",
    "superintendent": "Superintendent",
    "administrator": "Administrator",
    "lead": "Lead",
}


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


_PHONE_KEYWORDS = ["phone", "tel", "cell", "mob", "call us", "contact", "whatsapp", "telephone"]


def extract_phone(html_content: str, phone_patterns: list[str], prefixes: list[str]) -> str | None:
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        text_content = soup.get_text()

        lines = [ln.strip() for ln in text_content.split("\n") if ln.strip()]

        kw_lines: list[str] = []
        other_lines: list[str] = []
        for ln in lines:
            lower = ln.lower()
            if any(kw in lower for kw in _PHONE_KEYWORDS):
                kw_lines.append(ln)
            else:
                other_lines.append(ln)

        for pattern in phone_patterns:
            for ln in kw_lines:
                matches = re.findall(pattern, ln)
                if not matches:
                    continue
                for phone in matches:
                    normalized = normalize_phone(phone.strip(), prefixes)
                    if normalized:
                        return normalized

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


_CITY_KEYWORDS = ["city", "town", "locality", "municipality", "village"]


def extract_city(html_content: str) -> str | None:
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Semantic HTML attributes
        for el in soup.find_all(itemprop="addressLocality"):
            text = el.get("content") or el.get_text(strip=True)
            if text and len(text) < 60:
                return text.strip()

        for cls in ("city", "locality", "town"):
            for el in soup.find_all(class_=re.compile(cls, re.I)):
                text = el.get_text(strip=True)
                if text and len(text) < 60:
                    return text

        # 2. JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict):
                        loc = item.get("location") or item.get("address") or {}
                        if isinstance(loc, dict):
                            city = loc.get("addressLocality")
                            if isinstance(city, str) and city:
                                return city
            except Exception:
                continue

        # 3. "City: X" keyword patterns (must start with uppercase)
        text_content = soup.get_text()
        for kw in _CITY_KEYWORDS:
            m = re.search(rf"(?i)\b{re.escape(kw)}\s*[:.\-–—]\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)", text_content)
            if m:
                candidate = m.group(1).strip()
                if candidate[0].isupper():
                    return candidate

        # 4. Address proximity: capitalized word near phone/address keywords
        lines = [ln.strip() for ln in text_content.split("\n") if ln.strip()]
        for i, ln in enumerate(lines):
            if any(kw in ln.lower() for kw in ("phone", "tel:", "address:", "email:")):
                for j in range(max(0, i - 2), i):
                    m = re.search(
                        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*,\s*(?:South Africa|Kenya|Nigeria|Ghana|Egypt|Morocco|Algeria|Namibia|Botswana|Zambia|Zimbabwe|Tanzania|Uganda|Ethiopia|Angola|Mozambique)",
                        lines[j],
                    )
                    if m:
                        candidate = m.group(1).strip()
                        if candidate[0].isupper():
                            return candidate

        return None
    except Exception:
        return None


_STATE_KEYWORDS = ["state", "province", "region", "county", "district", "territory"]


def extract_state(html_content: str) -> str | None:
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Semantic HTML attributes
        for el in soup.find_all(itemprop="addressRegion"):
            text = el.get("content") or el.get_text(strip=True)
            if text and len(text) < 60:
                return text.strip()

        for cls in ("state", "province", "region", "county"):
            for el in soup.find_all(class_=re.compile(cls, re.I)):
                text = el.get_text(strip=True)
                if text and len(text) < 60:
                    return text

        # 2. JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict):
                        loc = item.get("location") or item.get("address") or {}
                        if isinstance(loc, dict):
                            region = loc.get("addressRegion")
                            if isinstance(region, str) and region:
                                return region
            except Exception:
                continue

        # 3. "State: X" keyword patterns (must start with uppercase)
        text_content = soup.get_text()
        for kw in _STATE_KEYWORDS:
            m = re.search(rf"(?i)\b{re.escape(kw)}\s*[:.\-–—]\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)", text_content)
            if m:
                candidate = m.group(1).strip()
                if candidate[0].isupper():
                    return candidate

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


def _is_valid_person_name(name: str) -> bool:
    if len(name) < 5 or len(name) > 50:
        return False
    if " " not in name:
        return False
    if "  " in name:
        return False
    words = name.split()
    if len(words) > 5:
        return False
    if set(words).issubset(_SKIP_WORDS):
        return False
    if any(w in _SKIP_WORDS for w in words):
        return False
    if any(c in name for c in ("@", "http", "www.", ".com", ".co.", ".in")):
        return False
    if any(p.search(name) for p in _ROLE_PATTERNS):
        return False
    if not _NAME_PATTERN.fullmatch(name):
        return False
    for word in words:
        if word in _COMPANY_INDICATORS:
            return False
        if word in _NON_PERSON_WORDS:
            return False
    noise_count = sum(1 for w in words if w in _NOISE_WORDS)
    if noise_count / len(words) >= 0.4:
        return False
    return True


def _extract_schema_person(soup: BeautifulSoup) -> tuple[str, str] | None:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get("@type") in ("Person", "Organization"):
                    if item["@type"] == "Person":
                        name = item.get("name", "")
                        if isinstance(name, str) and _is_valid_person_name(name):
                            role = item.get("jobTitle", "") or item.get("description", "") or ""
                            role = role if isinstance(role, str) and _is_valid_role(role) else "Not Found"
                            return name, role
                    member = item.get("founder") or item.get("employee") or item.get("member")
                    if isinstance(member, dict) and member.get("@type") == "Person":
                        name = member.get("name", "")
                        if isinstance(name, str) and _is_valid_person_name(name):
                            return name, "Not Found"
        except Exception:
            continue
    return None


def _try_name_from_email(html_content: str) -> tuple[str, str] | None:
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    emails = re.findall(pattern, html_content)
    for email in emails:
        local = email.split("@")[0]
        if "." in local and not local.startswith(("contact", "info", "sales", "support", "admin", "enquiry")):
            parts = local.split(".")
            if all(p.isalpha() and p[0].isupper() is False for p in parts):
                name = " ".join(p.capitalize() for p in parts)
                if _is_valid_person_name(name):
                    return name, "Not Found"
    return None


def _find_name_near_email(lines: list[str]) -> tuple[str, str] | None:
    for line in lines:
        if "@" not in line:
            continue
        names = _NAME_PATTERN.findall(line)
        for name in names:
            if _is_valid_person_name(name):
                role = _extract_role(line, name) or "Not Found"
                return name, role
    return None


def _is_valid_role(role: str) -> bool:
    return bool(role) and len(role) < 60


_TEAM_KEYWORDS = [
    "our team",
    "team",
    "board of directors",
    "board members",
    "board",
    "management",
    "leadership",
    "our people",
    "key personnel",
    "executives",
    "management team",
    "executive team",
    "our staff",
    "organizational structure",
    "meet the team",
    "meet our team",
    "team members",
]
_MEMBER_CLASSES = re.compile(r"team|member|person|staff|executive|board|profile|leadership|founder", re.IGNORECASE)
_ROLE_CLASSES = re.compile(r"role|title|position|designation|job", re.IGNORECASE)


def _extract_team_page_bs4(soup: BeautifulSoup) -> tuple[str, str] | None:
    """Extract person name + role from team/board HTML page structures.

    Handles:
      - <div class=\"team-member\"><h3>Name</h3><p>Role</p></div>
      - <li><strong>Name</strong> — Role</li>
      - <table><tr><td>Name</td><td>Role</td></tr></table>
      - Consecutive lines Name / Role under a \"Our Team\" header
    """
    # 1. Structured member containers with class hints
    for container in soup.find_all(["div", "li", "article"], class_=_MEMBER_CLASSES):
        name_el = container.find(["h2", "h3", "h4", "h5", "strong", "b"])
        if not name_el:
            continue
        name = name_el.get_text(strip=True)
        if not _is_valid_person_name(name):
            continue
        role_text = _get_role_text_from_container(container, name_el)
        if role_text:
            return name, role_text

    # 2. Table rows (Name | Role in <td> pairs)
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 2:
            name = cells[0].get_text(strip=True)
            if not _is_valid_person_name(name):
                continue
            role_match = _ROLE_PATTERNS[0].search(cells[1].get_text(strip=True))
            if role_match:
                return name, _normalize_role(role_match.group(1))

    # 3. Team sections identified by header keywords
    for tag in ["h1", "h2", "h3", "h4"]:
        for header in soup.find_all(tag):
            if header.get_text(strip=True).lower() not in _TEAM_KEYWORDS:
                continue
            parent = header.parent
            container_text = parent.get_text("\n") if parent else ""
            blob_lines = [ln.strip() for ln in container_text.split("\n") if ln.strip()]
            start = next((i for i, ln in enumerate(blob_lines) if ln.lower() in _TEAM_KEYWORDS), 1)
            for i in range(start, len(blob_lines) - 1):
                if not _is_valid_person_name(blob_lines[i]):
                    continue
                name = blob_lines[i]
                for j in range(i + 1, min(i + 4, len(blob_lines))):
                    rm = _ROLE_PATTERNS[0].search(blob_lines[j])
                    if rm:
                        has_interleaved = any(_is_valid_person_name(blob_lines[k]) for k in range(i + 1, j))
                        if not has_interleaved:
                            return name, _normalize_role(rm.group(1))

    return None


def _get_role_text_from_container(container, name_el) -> str | None:
    """Look for a role string near *name_el* inside *container*."""
    # By class hint
    role_el = container.find(["p", "span", "small", "em", "div"], class_=_ROLE_CLASSES)
    if not role_el:
        # Sibling of name element
        role_el = name_el.find_next_sibling(["p", "span", "small", "em"])
    if not role_el:
        # Any paragraph / span in container
        role_el = container.find(["p", "span", "small"])
    if not role_el:
        return None
    text = role_el.get_text(strip=True)
    rm = _ROLE_PATTERNS[0].search(text)
    if rm:
        return _normalize_role(rm.group(1))
    # Fallback: check same line as name for separator pattern
    line = name_el.parent.get_text(strip=True) if name_el.parent else ""
    if not line:
        return None
    for sep in ("—", "–", "-", "|"):
        if sep in line:
            parts = line.split(sep, 1)
            if _is_valid_person_name(parts[0].strip()):
                rm = _ROLE_PATTERNS[0].search(parts[1].strip())
                if rm:
                    return _normalize_role(rm.group(1))
    return None


def extract_contact_person(html_content: str) -> tuple[str, str]:
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        text_content = soup.get_text()

        # 1. Meta author tag
        author_tag = soup.find("meta", attrs={"name": "author"})
        if hasattr(author_tag, "get"):
            content = author_tag.get("content")  # type: ignore[union-attr]
            if content and isinstance(content, str) and _is_valid_person_name(content.strip()):
                return content.strip(), "Not Found"

        # 2. Schema.org JSON-LD
        schema_result = _extract_schema_person(soup)
        if schema_result:
            return schema_result

        lines = [ln.strip() for ln in text_content.split("\n") if ln.strip()]

        # 3. Name from email local part
        email_name = _try_name_from_email(html_content)
        if email_name:
            return email_name

        # 4. Name on same line as email
        near_email = _find_name_near_email(lines)
        if near_email:
            return near_email

        # 5. Team page BS4 structural extraction (container divs, table rows, team sections)
        team_result = _extract_team_page_bs4(soup)
        if team_result:
            return team_result

        # 6. Contextual person patterns (also handles "Name — Role" via group 2)
        for pattern in _PERSON_PATTERNS:
            for line in lines:
                match = pattern.search(line)
                if match:
                    name = match.group(1).strip()
                    if _is_valid_person_name(name):
                        if match.lastindex and match.lastindex >= 2:
                            role = match.group(2).strip()
                        else:
                            role = _extract_role(line, name) or "Not Found"
                        return name, role

        # 7. Role-prefixed names
        for pattern in _ROLE_PATTERNS:
            for line in lines:
                role_match = pattern.search(line)
                if role_match:
                    role = _normalize_role(role_match.group(1))
                    names_in_line = _NAME_PATTERN.findall(line)
                    for name in names_in_line:
                        if _is_valid_person_name(name):
                            return name, role

        return "Not Found", "Not Found"
    except Exception:
        return "Not Found", "Not Found"


def _normalize_role(role: str) -> str:
    return _ROLE_NORMALIZE.get(role.lower(), role)


def _extract_role(line: str, name: str) -> str | None:
    cleaned = line.replace(name, "").strip().lstrip(":-—–,;").strip()
    for pattern in _ROLE_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            return _normalize_role(match.group(1))
    return None
