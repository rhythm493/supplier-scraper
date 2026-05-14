from __future__ import annotations

import logging
import os
import shutil
import tempfile
from typing import TYPE_CHECKING

from scraper.browser import setup_driver

if TYPE_CHECKING:
    from selenium.webdriver import Chrome

    from scraper.config import Config

logger = logging.getLogger(__name__)


class ScrapeSession:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.temp_dir: str | None = None
        self.driver: Chrome | None = None

    def __enter__(self) -> ScrapeSession:
        self.temp_dir = tempfile.mkdtemp(prefix="scraper_")
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)
        self._original_dir = original_dir

        log_path = os.path.join(self.temp_dir, self.config.log_filename)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logging.getLogger().addHandler(file_handler)

        self.driver = setup_driver(
            use_undetected=True,
            page_load_timeout=self.config.page_load_timeout,
        )

        return self

    def __exit__(self, *args: object) -> None:
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed")
            except Exception:
                logger.exception("Error closing WebDriver")

        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info("Temp directory cleaned: %s", self.temp_dir)
            except Exception:
                logger.exception("Failed to clean temp dir: %s", self.temp_dir)

        if hasattr(self, "_original_dir"):
            os.chdir(self._original_dir)
