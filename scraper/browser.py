from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from patchright.sync_api import sync_playwright

if TYPE_CHECKING:
    from patchright.sync_api import Browser, Page, Playwright

logger = logging.getLogger(__name__)


def setup_page(page_load_timeout: int = 25) -> tuple[Playwright, Browser, Page]:
    pw = sync_playwright().start()
    browser = pw.chromium.launch(channel="chrome", headless=False)
    context = browser.new_context(no_viewport=True)
    page = context.new_page()
    page.set_default_timeout(page_load_timeout * 1000)
    page.route("**/*.{png,jpg,jpeg,gif,svg,ico,webp,woff,woff2,ttf,eot}", lambda route: route.abort())
    logger.info("Browser launched (channel=chrome)")
    return pw, browser, page
