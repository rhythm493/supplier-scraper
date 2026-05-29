# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.2
#   kernelspec:
#     display_name: .venv
#     language: python
#     name: python3
# ---

# %%
# --- Install dependencies (run once) ---
import subprocess, sys
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q",
    "-r", "scraper/requirements.txt",
])

# %%
# ============================================================
#   CONFIGURATION  —  Edit these values for your search
#   Copy-paste this cell to ChatGPT to generate overrides
# ============================================================

# --- Search queries ---
SEARCH_QUERIES = [
    "CSSD distributor in Africa",
    "Sterilization Reel distributor in Africa",
    "Sterilization pouches distributor in Africa",
    "Sterilization rolls supplier in Africa",
    "Doctor Gown distributor in Africa",
    "Sterile Gown supplier in Africa",
]

# --- Excluded sites (lowercase, partial match) ---
EXCLUDED_SITES = [
    "alibaba.com", "amazon.", "ebay.", "aliexpress.com", "indiamart.com",
    "tradeindia.com", "made-in-china.com", "walmart.com", "etsy.com",
    "linkedin.com", "wikipedia.org", "twitter.com", "instagram.com",
]

# --- Product categories for relevance filtering ---
PRODUCT_CATEGORIES = [
    "Sterilization and Infection Control", "infection control", "pouch",
    "indicator", "sterility", "biological indicator", "chemical indicator",
    "steam sterilizer", "EO sterilization", "plasma sterilization",
    "aseptic bags", "sterilization reels", "sterilization pouches",
    "sterility monitoring", "indicator strips", "autoclave tape",
    "surgeon gown", "isolation gown", "sterile gown", "sterilization", "sterile", "CSSD Consumables",
]

# --- Contact page detection keywords ---
CONTACT_KEYWORDS = ["contact", "about", "company", "directory", "support", "reach", "locations"]

# --- Country/region detection ---
COUNTRIES = [
    "Algeria", "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi",
    "Cabo Verde", "Cameroon", "Central African Republic", "Chad", "Comoros",
    "DRC", "Republic of the Congo", "Djibouti", "Egypt", "Equatorial Guinea",
    "Eritrea", "Eswatini", "Ethiopia", "Gabon", "Gambia", "Ghana",
    "Guinea", "Guinea-Bissau", "Ivory Coast", "Kenya", "Lesotho",
    "Liberia", "Libya", "Madagascar", "Malawi", "Mali", "Mauritania",
    "Mauritius", "Morocco", "Mozambique", "Namibia", "Niger", "Nigeria",
    "Rwanda", "Sao Tome and Principe", "Senegal", "Seychelles", "Sierra Leone",
    "Somalia", "South Africa", "South Sudan", "Sudan", "Tanzania", "Togo",
    "Tunisia", "Uganda", "Zambia", "Zimbabwe",
]
COUNTRY_KEYWORDS = ["Country:", "Location:", "Address:", "Headquarters:", "Based in"]

# --- Phone number detection ---
PHONE_PREFIXES = [
    "+213", "+244", "+229", "+267", "+226", "+257", "+238", "+237",
    "+236", "+235", "+269", "+243", "+242", "+253", "+20", "+240",
    "+291", "+268", "+251", "+241", "+220", "+233", "+224", "+245",
    "+225", "+254", "+266", "+231", "+218", "+261", "+265", "+223",
    "+222", "+230", "+212", "+258", "+264", "+227", "+234", "+250",
    "+239", "+221", "+248", "+232", "+252", "+27", "+211", "+249",
    "+255", "+228", "+216", "+256", "+260", "+263",
]
PHONE_PATTERNS = [
    r"\+?\d{1,3}[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}",
    r"\d{3}[\s-]?\d{3}[\s-]?\d{4}",
    r"\b\d{7,15}\b",
]

# --- E-commerce detection ---
ECOMMERCE_INDICATORS = [
    "add to cart", "buy now", "shopping cart", "checkout", "add to basket",
    "store", "shop", "purchase", "order", "price",
    "payment", "shipping", "delivery", "ecommerce",
]

# --- Output ---
OUTPUT_FILE = "CSSD_suppliers_africa.xlsx"

# --- Tuning ---
MAX_PAGES = 5
MAX_ATTEMPTS = 5
PAGE_TIMEOUT = 15
SCREENSHOTS = False

# %%
# %load_ext autoreload
# %autoreload 2

from scraper import Config, run_scraper
from IPython.display import clear_output, display
import pandas as pd

def on_progress(df, completed, total, found, name):
    clear_output(wait=True)
    pct = completed / total * 100 if total else 0
    bar_len = 30
    filled = int(bar_len * completed / total) if total else 0
    bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
    print(f"Progress: |{bar}| {completed}/{total} ({pct:.0f}%)  Chunk: {name}")
    print()
    display(df)

config = Config(
    search_queries=SEARCH_QUERIES,
    excluded_sites=EXCLUDED_SITES,
    product_categories=PRODUCT_CATEGORIES,
    contact_keywords=CONTACT_KEYWORDS,
    countries=COUNTRIES,
    country_keywords=COUNTRY_KEYWORDS,
    phone_prefixes=PHONE_PREFIXES,
    phone_patterns=PHONE_PATTERNS,
    ecommerce_indicators=ECOMMERCE_INDICATORS,
    output_filename=OUTPUT_FILE,
    max_search_pages=MAX_PAGES,
    max_search_attempts=MAX_ATTEMPTS,
    page_load_timeout=PAGE_TIMEOUT,
    screenshots=SCREENSHOTS,
)

df = run_scraper(config, on_progress=on_progress)
clear_output(wait=True)
print(f"Done \u2014 {len(df)} companies")
df
