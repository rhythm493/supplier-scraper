from __future__ import annotations

import concurrent.futures
import logging
import os
import sys
import tempfile
from collections.abc import Callable
from typing import TYPE_CHECKING

import pandas as pd

from scraper.dedup import deduplicate
from scraper.pipeline import extract_company_info
from scraper.search import google_search
from scraper.types import SearchResult

if TYPE_CHECKING:
    from scraper.config import Config

logger = logging.getLogger(__name__)

NUM_WORKERS = 4
COLUMNS = ["Company Name", "State", "City", "Country", "Phone Number", "Email", "Website", "Products"]


def _save_checkpoint(df: pd.DataFrame, output_path: str) -> None:
    try:
        df.to_excel(output_path, index=False)
    except ImportError:
        csv_path = output_path.rsplit(".", 1)[0] + ".csv"
        df.to_csv(csv_path, index=False)
        logger.warning("openpyxl not available, saved CSV: %s", csv_path)


def _process_chunk(
    company_items: list[tuple[str, SearchResult]],
    config: Config,
    worker_id: int,
) -> list[dict[str, str]]:
    from scraper.browser import setup_driver

    driver = setup_driver(use_undetected=True, page_load_timeout=config.page_load_timeout)
    chunk_results: list[dict[str, str]] = []

    try:
        for company_name, search_result in company_items:
            try:
                contact = extract_company_info(driver, search_result.url, company_name, config)
                if contact is not None:
                    chunk_results.append(
                        {
                            "Company Name": company_name,
                            "State": contact.state,
                            "City": contact.city,
                            "Country": contact.country,
                            "Phone Number": contact.phone,
                            "Email": contact.email,
                            "Website": search_result.url,
                            "Products": contact.products,
                        }
                    )
            except Exception:
                logger.exception("Worker %d failed on: %s", worker_id, company_name)
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return chunk_results


def run_scraper(
    config: Config,
    on_progress: Callable | None = None,
) -> pd.DataFrame:
    _setup_logging(config)
    original_cwd = os.getcwd()
    temp_dir = tempfile.mkdtemp(prefix="scraper_")
    os.chdir(temp_dir)

    all_rows: list[dict[str, str]] = []

    try:
        # Phase 1: Search — single browser
        from scraper.browser import setup_driver

        all_results: dict[str, SearchResult] = {}
        search_driver = setup_driver(use_undetected=True, page_load_timeout=config.page_load_timeout)
        try:
            for query in config.search_queries:
                logger.info("=== Search query: %s ===", query)
                for name, result in google_search(search_driver, query, config).items():
                    if name not in all_results:
                        all_results[name] = result
        finally:
            try:
                search_driver.quit()
            except Exception:
                pass

        logger.info("Found %d unique companies", len(all_results))
        items = list(all_results.items())
        if not items:
            return pd.DataFrame(columns=COLUMNS)

        # Phase 2: Parallel company visits
        num_items = len(items)
        num_workers = min(NUM_WORKERS, num_items)
        chunks: list[list] = [[] for _ in range(num_workers)]
        for i, item in enumerate(items):
            chunks[i % num_workers].append(item)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(_process_chunk, chunk, config, wid): wid for wid, chunk in enumerate(chunks) if chunk
            }
            completed_chunks = 0
            for future in concurrent.futures.as_completed(futures):
                try:
                    chunk_rows = future.result()
                    all_rows.extend(chunk_rows)
                except Exception:
                    logger.exception("Worker chunk failed")

                completed_chunks += 1
                if on_progress:
                    temp_df = pd.DataFrame(all_rows, columns=COLUMNS)
                    on_progress(
                        temp_df,
                        len(all_rows),
                        num_items,
                        True,
                        f"chunk {completed_chunks}/{len(futures)}",
                    )

        df = pd.DataFrame(all_rows, columns=COLUMNS)

    finally:
        os.chdir(original_cwd)
        import shutil

        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

    df = deduplicate(df, name_col="Company Name", url_col="Website")
    output_path = os.path.join(original_cwd, config.output_filename)
    _save_checkpoint(df, output_path)
    logger.info("Done — %d companies saved to %s", len(df), output_path)
    return df


def _setup_logging(config: Config) -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        root.addHandler(handler)
    logger.info("Scraper started — queries: %d, workers: %d", len(config.search_queries), NUM_WORKERS)
