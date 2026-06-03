from __future__ import annotations

import threading

from nicegui import app as nicegui_app
from nicegui import ui

from gui import pages
from gui.state import model_download, update_state
from scraper import __version__
from scraper.updater import check_for_update


def _background_update_check() -> None:
    def work():
        info = check_for_update()
        update_state["available"] = info.available
        update_state["latest_version"] = info.latest_version
        update_state["download_url"] = info.download_url
        update_state["release_url"] = info.release_url
        update_state["asset_name"] = info.asset_name
        update_state["size"] = info.size
        update_state["error"] = info.error

    threading.Thread(target=work, daemon=True).start()


def _download_model() -> None:
    from scraper import Config
    from scraper.llm_extractor import ensure_model, is_model_downloaded

    cfg = Config()
    if is_model_downloaded(cfg):
        model_download["status"] = "ready"
        model_download["message"] = "AI model ready"
        return

    model_download["status"] = "downloading"
    model_download["message"] = "Downloading AI model (267 MB)..."
    ensure_model(cfg, on_status=lambda msg: model_download.__setitem__("message", msg))
    if is_model_downloaded(cfg):
        model_download["status"] = "ready"
        model_download["message"] = "AI model ready"
    else:
        model_download["status"] = "error"
        model_download["message"] = "AI model unavailable — using regex only"


@ui.page("/")
def main_page() -> None:
    ui.colors(
        primary="#2563eb",
        secondary="#475569",
        accent="#3b82f6",
        positive="#16a34a",
        negative="#dc2626",
        warning="#d97706",
        info="#0ea5e9",
    )

    ui.add_head_html(
        """
<style>
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; }
</style>
"""
    )

    ui.query("body").classes("bg-slate-100")

    with ui.header().classes("bg-gradient-to-r from-slate-800 to-slate-700 shadow-md q-py-md q-px-lg"):
        with ui.row().classes("items-center justify-between w-full"):
            with ui.column().classes("gap-0"):
                ui.markdown("# Supplier Scraper").classes("text-white text-h5 q-mb-none")
                ui.markdown("Extract supplier and manufacturer data from Google Search results.").classes(
                    "text-slate-400 text-body2 q-mb-none"
                )
            with ui.row().classes("items-center gap-2"):
                model_badge = ui.badge("", color="amber-600").props("outline")
                model_badge.visible = False
                version_badge = ui.badge(f"v{__version__}", color="slate-600").props("outline")

    with ui.element("div").classes("max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6"):
        with ui.tabs().classes("w-full") as tabs:
            tab_config = ui.tab("Configuration", icon="tune")
            tab_run = ui.tab("Run", icon="play_arrow")
            tab_history = ui.tab("History", icon="history")
            tab_help = ui.tab("Help", icon="help_outline")

        with ui.tab_panels(tabs, value=tab_config).classes("w-full"):
            with ui.tab_panel(tab_config):
                pages.config.create()
            with ui.tab_panel(tab_run):
                pages.run.create()
            with ui.tab_panel(tab_history):
                pages.history.create()
            with ui.tab_panel(tab_help):
                pages.help.create()

    poll_timer = ui.timer(2, lambda: None, once=False)

    def _poll_update():
        if update_state["available"]:
            tab_help.props('badge="●"')
            version_badge.set_text(f"v{update_state['latest_version']} available")
            version_badge.props('color="positive"')
            poll_timer.deactivate()

    poll_timer = ui.timer(2, _poll_update, once=False)

    def _poll_model():
        if model_download["status"] == "downloading":
            model_badge.set_text(model_download["message"])
            model_badge.visible = True
            model_badge.props('color="amber-6"')
        elif model_download["status"] == "ready":
            model_badge.set_text("AI Ready")
            model_badge.visible = True
            model_badge.props('color="positive"')
        elif model_download["status"] == "error":
            model_badge.set_text(model_download["message"])
            model_badge.visible = True
            model_badge.props('color="negative"')
        else:
            model_badge.visible = False

    ui.timer(2, _poll_model, once=False)


nicegui_app.on_startup(_background_update_check)
nicegui_app.on_startup(lambda: threading.Thread(target=_download_model, daemon=True).start())
