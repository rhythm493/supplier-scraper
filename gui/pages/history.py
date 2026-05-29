from __future__ import annotations

from nicegui import events, ui

from gui.history import clear_history, delete_run, get_all_runs, get_config, get_results_download_path
from gui.pages.config import fill_from_history

_history_table: ui.table
_selected_run: int | None = None
_load_status: ui.markdown
_download_btn: ui.button
_download_path: str | None = None


def _refresh() -> None:
    df = get_all_runs()
    _history_table.rows = df.to_dict("records")


def _select(e: events.GenericEventArguments) -> None:
    global _selected_run, _download_path
    data = e.args
    if isinstance(data, dict) and "row" in data:
        data = data["row"]
    if not isinstance(data, dict) or "ID" not in data:
        return
    _selected_run = int(data["ID"])
    _download_path = get_results_download_path(_selected_run)
    _load_status.set_content(f"Selected **Run #{_selected_run}** — click **Load Config** to restore settings.")
    _download_btn.set_visibility(bool(_download_path))


def _do_download() -> None:
    if _download_path:
        ui.download(_download_path)


def _load_config() -> None:
    if _selected_run is None:
        ui.notify("Select a run from the table first", type="warning")
        return
    cfg = get_config(_selected_run)
    fill_from_history(cfg)
    ui.notify(f"Config loaded from Run #{_selected_run}")


def _delete() -> None:
    global _selected_run, _download_path
    if _selected_run is None:
        ui.notify("No run selected", type="warning")
        return
    delete_run(_selected_run)
    _selected_run = None
    _download_path = None
    _refresh()
    _load_status.set_content("Run deleted.")
    _download_btn.set_visibility(False)


def _clear_all() -> None:
    global _selected_run, _download_path
    clear_history()
    _selected_run = None
    _download_path = None
    _refresh()
    _load_status.set_content("All history cleared.")
    _download_btn.set_visibility(False)


def refresh_display() -> None:
    _refresh()


def create() -> None:
    global _history_table, _load_status, _download_btn

    _history_table = ui.table(
        columns=[
            {"name": "ID", "label": "ID", "field": "ID"},
            {"name": "Timestamp", "label": "Timestamp", "field": "Timestamp"},
            {"name": "Queries", "label": "Queries", "field": "Queries"},
            {"name": "Results", "label": "Results", "field": "Results"},
            {"name": "Status", "label": "Status", "field": "Status"},
        ],
        rows=[],
    ).classes("w-full")
    _history_table.on("rowClick", _select)

    _load_status = ui.markdown("Select a run from the table, then click **Load Config** to restore its settings.")

    with ui.row().classes("w-full gap-4"):
        ui.button("Refresh", on_click=_refresh, icon="refresh")
        ui.button(
            "Load Config",
            on_click=_load_config,
            icon="settings_backup_restore",
        ).props('color="primary"')
        ui.button("Delete", on_click=_delete, icon="delete")
        ui.button("Clear All", on_click=_clear_all, icon="delete_sweep")

    _download_btn = ui.button("Download Results", icon="download", on_click=_do_download).props("outline")
    _download_btn.set_visibility(False)

    _refresh()
