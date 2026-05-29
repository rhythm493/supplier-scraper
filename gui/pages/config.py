from __future__ import annotations

import json
import tempfile
from typing import Any

from nicegui import events, ui

from gui.state import (
    DEFAULT_CONTACT_KEYWORDS,
    DEFAULT_COUNTRIES,
    DEFAULT_COUNTRY_KEYWORDS,
    DEFAULT_ECOMMERCE_INDICATORS,
    DEFAULT_EXCLUDED_SITES,
    DEFAULT_PHONE_PATTERNS,
    DEFAULT_PHONE_PREFIXES,
    DEFAULT_PRODUCT_CATEGORIES,
    DEFAULT_SEARCH_QUERIES,
    build_config,
)
from scraper import Config

_queries: ui.textarea
_excluded: ui.textarea
_categories: ui.textarea
_countries: ui.textarea
_country_kw: ui.textarea
_contact_kw: ui.textarea
_ecom: ui.textarea
_prefixes: ui.textarea
_patterns: ui.textarea
_output: ui.input
_max_pages: ui.slider
_max_attempts: ui.slider
_timeout: ui.slider
_screenshots: ui.checkbox


def _join(items: list[str]) -> str:
    return "\n".join(items) if items else ""


def _split(text: str) -> list[str]:
    return [s.strip() for s in text.strip().split("\n") if s.strip()]


def _reset() -> None:
    _queries.set_value(_join(DEFAULT_SEARCH_QUERIES))
    _excluded.set_value(_join(DEFAULT_EXCLUDED_SITES))
    _categories.set_value(_join(DEFAULT_PRODUCT_CATEGORIES))
    _countries.set_value(_join(DEFAULT_COUNTRIES))
    _country_kw.set_value(_join(DEFAULT_COUNTRY_KEYWORDS))
    _contact_kw.set_value(_join(DEFAULT_CONTACT_KEYWORDS))
    _ecom.set_value(_join(DEFAULT_ECOMMERCE_INDICATORS))
    _prefixes.set_value(_join(DEFAULT_PHONE_PREFIXES))
    _patterns.set_value(_join(DEFAULT_PHONE_PATTERNS))
    _output.set_value("suppliers.xlsx")
    _max_pages.set_value(5)
    _max_attempts.set_value(5)
    _timeout.set_value(15)
    _screenshots.set_value(False)
    ui.notify("Defaults restored")


def _import_cfg(e: events.UploadEventArguments) -> None:
    content: bytes = e.content  # type: ignore
    try:
        cfg = json.loads(content)
    except Exception:
        ui.notify("Invalid JSON file", type="negative")
        return
    _queries.set_value(_join(cfg.get("search_queries", DEFAULT_SEARCH_QUERIES)))
    _excluded.set_value(_join(cfg.get("excluded_sites", DEFAULT_EXCLUDED_SITES)))
    _categories.set_value(_join(cfg.get("product_categories", DEFAULT_PRODUCT_CATEGORIES)))
    _countries.set_value(_join(cfg.get("countries", DEFAULT_COUNTRIES)))
    _country_kw.set_value(_join(cfg.get("country_keywords", DEFAULT_COUNTRY_KEYWORDS)))
    _contact_kw.set_value(_join(cfg.get("contact_keywords", DEFAULT_CONTACT_KEYWORDS)))
    _ecom.set_value(_join(cfg.get("ecommerce_indicators", DEFAULT_ECOMMERCE_INDICATORS)))
    _prefixes.set_value(_join(cfg.get("phone_prefixes", DEFAULT_PHONE_PREFIXES)))
    _patterns.set_value(_join(cfg.get("phone_patterns", DEFAULT_PHONE_PATTERNS)))
    _output.set_value(cfg.get("output_filename", "suppliers.xlsx"))
    _max_pages.set_value(int(cfg.get("max_search_pages", 5)))
    _max_attempts.set_value(int(cfg.get("max_search_attempts", 5)))
    _timeout.set_value(int(cfg.get("page_load_timeout", 15)))
    _screenshots.set_value(bool(cfg.get("screenshots", False)))
    ui.notify("Config imported")


def _export_cfg() -> None:
    cfg = {
        "search_queries": _split(_queries.value),
        "excluded_sites": _split(_excluded.value),
        "product_categories": _split(_categories.value),
        "countries": _split(_countries.value),
        "country_keywords": _split(_country_kw.value),
        "contact_keywords": _split(_contact_kw.value),
        "ecommerce_indicators": _split(_ecom.value),
        "phone_prefixes": _split(_prefixes.value),
        "phone_patterns": _split(_patterns.value),
        "output_filename": _output.value,
        "max_search_pages": int(_max_pages.value),
        "max_search_attempts": int(_max_attempts.value),
        "page_load_timeout": int(_timeout.value),
        "screenshots": bool(_screenshots.value),
    }
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, prefix="scraper_config_")
    json.dump(cfg, tmp, indent=2)
    tmp.close()
    ui.download(tmp.name, filename="config.json")


def get_config() -> Config:
    return build_config(
        search_queries=_split(_queries.value),
        excluded_sites=_split(_excluded.value),
        product_categories=_split(_categories.value),
        contact_keywords=_split(_contact_kw.value),
        countries=_split(_countries.value),
        country_keywords=_split(_country_kw.value),
        ecommerce_indicators=_split(_ecom.value),
        phone_prefixes=_split(_prefixes.value),
        phone_patterns=_split(_patterns.value),
        output_filename=_output.value,
        max_search_pages=int(_max_pages.value),
        max_search_attempts=int(_max_attempts.value),
        page_load_timeout=int(_timeout.value),
        screenshots=bool(_screenshots.value),
    )


def fill_from_history(cfg: dict[str, Any]) -> None:
    _queries.set_value(_join(cfg.get("search_queries", [])))
    _excluded.set_value(_join(cfg.get("excluded_sites", [])))
    _categories.set_value(_join(cfg.get("product_categories", [])))
    _countries.set_value(_join(cfg.get("countries", [])))
    _country_kw.set_value(_join(cfg.get("country_keywords", [])))
    _contact_kw.set_value(_join(cfg.get("contact_keywords", [])))
    _ecom.set_value(_join(cfg.get("ecommerce_indicators", [])))
    _prefixes.set_value(_join(cfg.get("phone_prefixes", [])))
    _patterns.set_value(_join(cfg.get("phone_patterns", [])))
    _output.set_value(cfg.get("output_filename", "suppliers.xlsx"))
    _max_pages.set_value(int(cfg.get("max_search_pages", 5)))
    _max_attempts.set_value(int(cfg.get("max_search_attempts", 5)))
    _timeout.set_value(int(cfg.get("page_load_timeout", 15)))
    _screenshots.set_value(bool(cfg.get("screenshots", False)))


def create() -> None:
    global _queries, _excluded, _categories, _countries, _country_kw, _contact_kw
    global _ecom, _prefixes, _patterns, _output, _max_pages, _max_attempts, _timeout, _screenshots

    with ui.card().classes("w-full"):
        ui.markdown("### Search Settings")
        _queries = (
            ui.textarea(
                label="Search Queries (one per line)",
                value=_join(DEFAULT_SEARCH_QUERIES),
            )
            .classes("w-full")
            .props("outlined rows=6")
        )
        _excluded = (
            ui.textarea(
                label="Excluded Sites (one per line) — partial match, lowercase",
                value=_join(DEFAULT_EXCLUDED_SITES),
            )
            .classes("w-full")
            .props("outlined rows=4")
        )
        with ui.row().classes("w-full gap-x-8 gap-y-2"):
            with ui.column().classes("flex-1 min-w-[160px]"):
                _max_pages = ui.slider(min=1, max=20, step=1, value=5)
                ui.label("Max Search Pages").classes("text-sm text-gray-500")
            with ui.column().classes("flex-1 min-w-[160px]"):
                _max_attempts = ui.slider(min=1, max=10, step=1, value=5)
                ui.label("Max Search Attempts").classes("text-sm text-gray-500")
            with ui.column().classes("flex-1 min-w-[160px]"):
                _timeout = ui.slider(min=5, max=60, step=5, value=15)
                ui.label("Page Load Timeout (s)").classes("text-sm text-gray-500")

    with ui.card().classes("w-full"):
        ui.markdown("### Filtering")
        _categories = (
            ui.textarea(
                label="Product Categories (one per line)",
                value=_join(DEFAULT_PRODUCT_CATEGORIES),
            )
            .classes("w-full")
            .props("outlined rows=5")
        )
        _countries = (
            ui.textarea(
                label="Target Countries (one per line)",
                value=_join(DEFAULT_COUNTRIES),
            )
            .classes("w-full")
            .props("outlined rows=4")
        )
        _country_kw = (
            ui.textarea(
                label="Country Keywords (one per line)",
                value=_join(DEFAULT_COUNTRY_KEYWORDS),
            )
            .classes("w-full")
            .props("outlined rows=2")
        )

    with ui.row().classes("w-full gap-4 items-end"):
        with ui.column().classes("flex-1"):
            _output = (
                ui.input(
                    label="Output Filename",
                    value="suppliers.xlsx",
                )
                .classes("w-full")
                .props("outlined")
            )
        _screenshots = ui.checkbox(text="Take Screenshots", value=False)

    with ui.expansion(text="Advanced Settings", icon="settings").classes("w-full"):
        _contact_kw = (
            ui.textarea(
                label="Contact Page Keywords",
                value=_join(DEFAULT_CONTACT_KEYWORDS),
            )
            .classes("w-full")
            .props("outlined rows=2")
        )
        _ecom = (
            ui.textarea(
                label="E-commerce Indicators (one per line)",
                value=_join(DEFAULT_ECOMMERCE_INDICATORS),
            )
            .classes("w-full")
            .props("outlined rows=4")
        )
        _prefixes = (
            ui.textarea(
                label="Phone Prefixes (one per line)",
                value=_join(DEFAULT_PHONE_PREFIXES),
            )
            .classes("w-full")
            .props("outlined rows=5")
        )
        _patterns = (
            ui.textarea(
                label="Phone Regex Patterns (one per line)",
                value=_join(DEFAULT_PHONE_PATTERNS),
            )
            .classes("w-full")
            .props("outlined rows=3")
        )

    with ui.row().classes("w-full gap-4"):
        ui.upload(label="Import Config", on_upload=_import_cfg).props('flat color="primary"')
        ui.button("Export Config", on_click=_export_cfg).props("outline")
        ui.button("Reset Defaults", on_click=_reset).props("outline")
