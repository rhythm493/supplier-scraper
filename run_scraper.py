#!/usr/bin/env python3
"""CLI entry point for the Supplier Scraper GUI application."""

from __future__ import annotations

import argparse
import logging
import multiprocessing
import sys
from importlib.metadata import version as _pkg_version


def _get_version() -> str:
    try:
        ver = _pkg_version("supplier-scraper")
    except Exception:
        from scraper import __version__

        ver = __version__
    return ver.removeprefix("v")


def main() -> int:
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description="Supplier Scraper GUI")
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Open in web browser instead of native desktop window",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to run the server on (default: 8080)",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit",
    )
    args = parser.parse_args()

    VERSION = _get_version()

    if args.version:
        print(f"Supplier Scraper v{VERSION}")
        return 0

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    logging.getLogger().info("Starting Supplier Scraper GUI...")
    print("=" * 50)
    print(f"  Supplier Scraper v{VERSION}")
    print("=" * 50)

    from nicegui import ui

    kwargs: dict = {
        "title": "Supplier Scraper",
        "host": "127.0.0.1",
        "port": args.port,
        "dark": False,
        "reload": False,
        "show": True,
    }

    if not args.browser:
        try:
            import webview  # noqa: F401

            kwargs["native"] = True
            kwargs["show"] = False
        except ImportError:
            logging.getLogger().warning(
                "pywebview not installed — falling back to browser. Install: pip install pywebview"
            )

    ui.run(**kwargs)
    return 0


if __name__ in {"__main__", "__mp_main__"}:
    sys.exit(main())
