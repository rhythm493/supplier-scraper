# Supplier Scraper — Module Refactor

## What This Is

A refactored Google-based supplier/medical device manufacturer scraper. Originally a single 9543-line Jupyter notebook with 2 nearly-identical cells (Africa CSSD + India medical device), it is now a proper Python package (`scraper/`) driven by a 2-cell notebook.

## Architecture

```
scraper/           # Python package (10 modules)
__init__.py        # Exports: Config, run_scraper
types.py           # Dataclasses: ContactInfo, SearchResult
config.py          # Config dataclass (flat, all fields visible in notebook)
validators.py      # normalize_email, normalize_phone, normalize_country, extract_domain
extractors.py      # extract_email, extract_phone, extract_country, extract_products
browser.py         # setup_driver() — OS-aware Chrome binary detection
search.py          # google_search() — multi-attempt, multi-page, CAPTCHA detection
pipeline.py        # extract_company_info() — homepage→contact→about waterfall
dedup.py           # deduplicate() — exact domain + fuzzy name
session.py         # ScrapeSession context manager (unused by runner, kept for reference)
runner.py          # run_scraper() — orchestrator: Phase 1 search, Phase 2 parallel visits

Supplier_Scraper.ipynb  # 2 cells: config (81 lines) + run (38 lines)
```

## Data Flow

```
Notebook Cell 1 (config vars) → Config() → run_scraper(config, on_progress)
                                                        │
                                          ┌─────────────┴──────────────┐
                                    Phase 1 (search)             Phase 2 (visit)
                                          │                          │
                                   setup_driver()           ThreadPoolExecutor (≤4)
                                          │                          │
                                google_search() per query    worker: setup_driver()
                                          │                     visit chunk companies
                                search_driver.quit()          extract_company_info()
                                          │                          │
                                    list of SearchResults      driver.quit()
                                          │                          │
                                          └──────────┬──────────────┘
                                                     │
                                              deduplicate() → to_excel()
```

### Key Design Decisions

- **Flat Config**: All fields are dataclass attributes on `Config` — no nested profiles. The notebook cell has every variable visible for editing.
- **Two-phase execution**: Phase 1 uses one browser for Google search, quits it. Phase 2 spawns up to 4 browsers via ThreadPoolExecutor, each processing a round-robin chunk of companies in its own driver. Separate browsers avoid Selenium thread-safety issues.
- **CAPTCHA handling**: `wait_for_captcha()` polls every 3s for up to 5 minutes, checking text indicators + iframe detection. Prints instructions to stdout. User solves in browser window, script auto-resumes.
- **Relevance filtering**: `_check_relevance()` scores text against `product_categories` + manufacturing terms. Score >= 2 passes. Tuned to not kill legit manufacturer sites.
- **E-commerce filtering**: `_is_ecommerce()` requires both text-score >= 6 AND structural elements (cart buttons, grids) >= 3. Deliberately excludes standalone "product" word from indicators.
- **Dedup**: Two-stage — exact domain match first, then `SequenceMatcher` fuzzy name match (threshold 0.85).
- **Screenshot cleanup**: All work happens in `tempfile.mkdtemp()`, deleted in `finally` block.
- **Cross-platform Chrome detection**: Windows (Program Files, local), Linux (which, snap, flatpak), macOS (/Applications).
- **Humanization**: Cookie clearing on first attempt only. Random delays via `random.uniform()`. Character-by-character typing. Random scrolling. Randomized query suffixes.
- **CSV fallback**: If `openpyxl` is missing, `to_excel` falls back to `to_csv` silently.

## Output Columns

Company Name | State | City | Country | Phone Number | Email | Website | Products

## Running

```python
# Cell 2 of notebook
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
```

## Notebook Editing (Jupytext)

Edit `Supplier_Scraper.py` (clean Python, `# %%` cell markers) instead of the raw `.ipynb`. Then sync:

```bash
jupytext --sync Supplier_Scraper.ipynb
```

To edit in Jupyter directly and sync back to `.py`:
```bash
jupytext --sync Supplier_Scraper.ipynb
```

The `jupytext.toml` at the project root configures the paired format.

## Dependencies

- Python 3.10+
- selenium, undetected-chromedriver, webdriver-manager
- pandas, openpyxl
- beautifulsoup4, jupytext
- Google Chrome / Chromium

## Files At A Glance

| Module | Lines | Key Functions |
|---|---|---|
| `types.py` | 22 | `ContactInfo`, `SearchResult` |
| `config.py` | 34 | `Config` dataclass |
| `validators.py` | 49 | `normalize_email`, `normalize_phone`, `normalize_country`, `extract_domain` |
| `extractors.py` | 91 | `extract_email`, `extract_phone`, `extract_country`, `extract_products` |
| `browser.py` | 280 | `setup_driver`, `_find_chrome_binary`, `_setup_undetected`, `_setup_regular`, `_ensure_cft` |
| `search.py` | 340 | `google_search`, `detect_captcha`, `wait_for_captcha`, `_extract_search_results`, `_navigate_next_page` |
| `pipeline.py` | 176 | `extract_company_info`, `_scrape_page`, `_find_page`, `_check_relevance`, `_is_ecommerce` |
| `dedup.py` | 49 | `deduplicate`, `_fuzzy_dedup_names` |
| `session.py` | 63 | `ScrapeSession` (unused) |
| `runner.py` | 164 | `run_scraper`, `_process_chunk`, `_save_checkpoint` |
| `__init__.py` | 4 | Exports |
| `Supplier_Scraper.ipynb` | 190 lines | 3 cells (install + config + run) |
| `Supplier_Scraper.py` | 155 lines | Jupytext percent-script paired with notebook |

## Distribution

Releases build a cross-platform zip via GitHub Actions containing:
`Supplier_Scraper.ipynb`, `scraper/`, `requirements.txt` (inside scraper/), and `README.md`.

Chrome for Testing + ChromeDriver auto-download on first run via `_ensure_cft()` in `browser.py`.
Cache is stored in `chrome-cache/{platform}/{version}/` relative to the project root.

## Notebook Editing (Jupytext)

Edit `Supplier_Scraper.py` (clean Python, `# %%` cell markers) instead of the raw `.ipynb`. Then sync:

```bash
jupytext --sync Supplier_Scraper.ipynb
```

To edit in Jupyter directly and sync back to `.py`:
```bash
jupytext --sync Supplier_Scraper.ipynb
```

The `jupytext.toml` at the project root configures the paired format.

## What Was Refactored

Original problems (all fixed):
- **Undefined variable**: `DENTAL_PRODUCT_CATEGORIES` referenced before definition
- **Massive code duplication**: 1191-line Cell 1 vs 1017-line Cell 2, ~95% identical
- **9543 lines of pip install output** bloating the notebook
- **Windows-only hardcoded Chrome paths**
- **Bare `except: pass` blocks** silencing all errors
- **No type hints** anywhere
- **Deterministic "random" delays** using `hash()` → same seed per session
- **Aggressive e-commerce filtering** killing legitimate manufacturers (>threshold 5 with "product" text match)
- **Output file lost** — ScrapeSession chdir into temp dir, save happened inside, rmtree deleted it
- **Missing output fields** — State, City, Products extracted but never included in output DataFrame
