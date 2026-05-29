from __future__ import annotations

from nicegui import ui

from gui import pages


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
        ui.markdown("# Supplier Scraper").classes("text-white text-h5 q-mb-none")
        ui.markdown("Extract supplier and manufacturer data from Google Search results.").classes(
            "text-slate-400 text-body2 q-mb-none"
        )

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
