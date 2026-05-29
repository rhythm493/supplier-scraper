#!/usr/bin/env python3
"""CLI entry point for the Supplier Scraper GUI application."""

from __future__ import annotations

import argparse
import logging
import multiprocessing
import sys


def main() -> int:
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description="Supplier Scraper GUI")
    parser.add_argument(
        "--native",
        action="store_true",
        help="Launch in native desktop window (requires pywebview + GTK/Qt)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to run the server on (default: 8080)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    import gui.main  # noqa: F401

    logging.getLogger().info("Starting Supplier Scraper GUI...")
    print("=" * 50)
    print("  Supplier Scraper GUI")
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

    if args.native:
        try:
            import webview  # noqa: F401

            kwargs["native"] = True
            kwargs["show"] = False
        except ImportError:
            logging.getLogger().warning("--native requires pywebview. Install: pip install pywebview")
            kwargs["show"] = True

    ui.run(**kwargs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
