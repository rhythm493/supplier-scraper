#!/usr/bin/env python3
"""CLI entry point for the Supplier Scraper GUI application.

Usage:
    python run_scraper.py            # Launch the Gradio web UI
    python run_scraper.py --share    # Launch with public share link
    python run_scraper.py --port 8080
"""

from __future__ import annotations

import argparse
import logging
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Supplier Scraper GUI")
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public share link via Gradio",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to run the server on",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    from gradio.themes import Soft as SoftTheme

    from gui.app import create_ui

    ui = create_ui()

    print("=" * 50)
    print("  Supplier Scraper GUI")
    print("  Open the URL below in your browser to access the application")
    print("=" * 50)

    launch_kwargs: dict = {
        "show_error": True,
        "theme": SoftTheme(),
        "inbrowser": True,
    }
    if args.share:
        launch_kwargs["share"] = True
    if args.port is not None:
        launch_kwargs["server_port"] = args.port

    ui.launch(**launch_kwargs)  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    sys.exit(main())
