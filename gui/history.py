from __future__ import annotations

import io
import json
import os
import sqlite3
import tempfile
from datetime import datetime
from typing import Any

import pandas as pd

from scraper import Config

_HISTORY_DIR = os.path.expanduser("~/.supplier-scraper")
_DB_PATH = os.path.join(_HISTORY_DIR, "history.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(_HISTORY_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                config_json TEXT NOT NULL,
                num_results INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'unknown',
                error_message TEXT,
                results_csv TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def save_run(
    config: Config,
    num_results: int,
    status: str,
    error_message: str | None,
    df: pd.DataFrame | None,
) -> int:
    config_dict = {
        "search_queries": config.search_queries,
        "excluded_sites": config.excluded_sites,
        "product_categories": config.product_categories,
        "countries": config.countries,
        "country_keywords": config.country_keywords,
        "contact_keywords": config.contact_keywords,
        "phone_prefixes": config.phone_prefixes,
        "phone_patterns": config.phone_patterns,
        "ecommerce_indicators": config.ecommerce_indicators,
        "output_filename": config.output_filename,
        "max_search_pages": config.max_search_pages,
        "max_search_attempts": config.max_search_attempts,
        "page_load_timeout": config.page_load_timeout,
        "screenshots": config.screenshots,
    }

    results_csv: str | None = None
    if df is not None and not df.empty:
        results_csv = df.to_csv(index=False)

    conn = _get_conn()
    try:
        cursor = conn.execute(
            """
            INSERT INTO runs (timestamp, config_json, num_results, status, error_message, results_csv)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(),
                json.dumps(config_dict),
                num_results,
                status,
                error_message,
                results_csv,
            ),
        )
        conn.commit()
        assert cursor.lastrowid is not None
        return cursor.lastrowid
    finally:
        conn.close()


def get_all_runs() -> pd.DataFrame:
    init_db()
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT id, timestamp, config_json, num_results, status, error_message
            FROM runs
            ORDER BY id DESC
            LIMIT 100
        """).fetchall()

        _columns = ["ID", "Timestamp", "Queries", "Results", "Status"]
        records = []
        for row in rows:
            cfg = json.loads(row["config_json"])
            queries = cfg.get("search_queries", [])
            queries_str = "; ".join(queries)
            if len(queries_str) > 80:
                queries_str = queries_str[:77] + "..."
            records.append(
                {
                    "ID": row["id"],
                    "Timestamp": row["timestamp"],
                    "Queries": queries_str,
                    "Results": row["num_results"],
                    "Status": row["status"],
                }
            )
        if not records:
            return pd.DataFrame(columns=_columns)
        return pd.DataFrame(records)
    finally:
        conn.close()


def get_run(run_id: int) -> dict[str, Any]:
    init_db()
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise ValueError(f"Run {run_id} not found")
        return dict(row)
    finally:
        conn.close()


def get_results_df(run_id: int) -> pd.DataFrame | None:
    row = get_run(run_id)
    csv_text = row.get("results_csv")
    if not csv_text:
        return None
    return pd.read_csv(io.StringIO(csv_text))


def get_results_download_path(run_id: int) -> str | None:
    df = get_results_df(run_id)
    if df is None:
        return None
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, prefix=f"supplier_results_{run_id}_")
    df.to_csv(tmp.name, index=False)
    tmp.close()
    return tmp.name


def get_config(run_id: int) -> dict[str, Any]:
    row = get_run(run_id)
    return json.loads(row["config_json"])


def delete_run(run_id: int) -> None:
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        conn.commit()
    finally:
        conn.close()


def clear_history() -> None:
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM runs")
        conn.commit()
    finally:
        conn.close()
