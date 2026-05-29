from __future__ import annotations

import pandas as pd
from nicegui import ui

from gui.history import save_run
from gui.pages.config import get_config
from gui.pages.history import refresh_display
from gui.state import (
    COLUMNS,
    cancel_event,
    patch_captcha_handler,
    scrape_state,
    start_scrape,
)

_status: ui.markdown
_log: ui.log
_table: ui.table
_download: ui.button
_captcha: ui.markdown
_start_btn: ui.button
_cancel_btn: ui.button
_download_path: str | None = None


def _do_start() -> None:
    config = get_config()
    patch_captcha_handler()
    start_scrape(config)
    _start_btn.props("loading disable")
    _start_btn.set_visibility(False)
    _cancel_btn.set_visibility(True)
    _cancel_btn.props(remove="loading")
    _cancel_btn.enable()


def _do_cancel() -> None:
    if cancel_event is not None:
        cancel_event.set()
    _cancel_btn.props("loading disable")
    scrape_state["phase"] = "Cancelling — finishing current tasks..."


def _do_download() -> None:
    global _download_path
    if _download_path:
        ui.download(_download_path)


def _reset_buttons() -> None:
    _start_btn.props(remove="loading disable")
    _start_btn.set_visibility(True)
    _cancel_btn.props(remove="loading")
    _cancel_btn.set_visibility(False)


def _poll() -> None:
    if not scrape_state.get("done") and not scrape_state.get("error"):
        phase = scrape_state.get("phase", "")
        if phase:
            _status.set_content(f"**{phase}**")
        _captcha.visible = scrape_state.get("captcha", False)
        log_lines = scrape_state.get("log", [])
        if log_lines:
            _log.clear()
            for line in log_lines[-5:]:
                _log.push(line)  # type: ignore
        df = scrape_state.get("df")
        if df is not None and not df.empty:
            _table.rows = df.to_dict("records")
        return

    _reset_buttons()

    if scrape_state.get("error"):
        _status.set_content(f"**Error:** {scrape_state['error']}")
        log_lines = scrape_state.get("log", [])
        if log_lines:
            _log.clear()
            for line in log_lines[-5:]:
                _log.push(line)  # type: ignore
        return

    global _download_path
    _download_path = scrape_state.get("output_path", None)
    _download.set_visibility(bool(_download_path))
    df = scrape_state.get("df", pd.DataFrame(columns=COLUMNS))
    if df is not None and not df.empty:
        _table.rows = df.to_dict("records")
    log_lines = scrape_state.get("log", [])
    if log_lines:
        _log.clear()
        for line in log_lines[-5:]:
            _log.push(line)  # type: ignore

    save_run(
        config=get_config(),
        num_results=len(df) if df is not None else 0,
        status="cancelled" if scrape_state.get("phase", "").startswith("Cancelled") else "success",
        error_message=scrape_state.get("error"),
        df=df if df is not None else pd.DataFrame(columns=COLUMNS),
    )
    refresh_display()


def create() -> None:
    global _status, _log, _table, _download, _captcha, _start_btn, _cancel_btn

    _status = ui.markdown("**Status:** Ready. Configure your search and click **Start Scraping**.")

    _captcha = ui.markdown(
        "**CAPTCHA DETECTED** — Switch to the Chrome browser window and solve it. "
        "The scraper will resume automatically once solved."
    ).classes("bg-amber-50 border border-amber-300 rounded-lg p-4 text-amber-800 mb-4")
    _captcha.visible = False

    _log = ui.log(max_lines=100).classes("w-full h-40 text-sm font-mono bg-slate-900 text-slate-200 rounded-lg p-3")

    with ui.card().classes("w-full overflow-x-auto"):
        _table = ui.table(
            columns=[{"name": c, "label": c, "field": c} for c in COLUMNS],
            rows=[],
        ).classes("w-full")

    with ui.row().classes("w-full gap-4 flex-wrap"):
        _start_btn = ui.button(
            "Start Scraping",
            on_click=_do_start,
            icon="play_arrow",
        ).props('color="primary" size="lg"')
        _cancel_btn = ui.button(
            "Cancel",
            on_click=_do_cancel,
            icon="stop",
        ).props('color="negative" size="lg"')
        _cancel_btn.set_visibility(False)

    _download = ui.button("Download Excel", icon="download", on_click=_do_download).props('color="positive" outline')
    _download.set_visibility(False)

    ui.timer(0.5, _poll, active=True)  # type: ignore[call-arg]
