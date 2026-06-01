from __future__ import annotations

import threading

from nicegui import ui

from gui.state import update_state
from scraper import __version__
from scraper.updater import check_for_update, download_update

_update_label: ui.label | None = None
_update_btn: ui.button | None = None


def _set_status(text: str) -> None:
    if _update_label is not None:
        _update_label.set_text(text)


def _do_check() -> None:
    if update_state["checking"]:
        return

    update_state["checking"] = True
    update_state["error"] = ""
    _set_status("Checking...")

    def work():
        info = check_for_update(on_progress=lambda msg: _set_status(msg))
        update_state["available"] = info.available
        update_state["latest_version"] = info.latest_version
        update_state["download_url"] = info.download_url
        update_state["release_url"] = info.release_url
        update_state["asset_name"] = info.asset_name
        update_state["size"] = info.size
        update_state["error"] = info.error
        update_state["checking"] = False
        _refresh_ui()

    threading.Thread(target=work, daemon=True).start()


def _do_download() -> None:
    url = update_state["download_url"]
    if not url or update_state["downloading"]:
        return

    update_state["downloading"] = True
    _set_status("Downloading...")

    def work():
        path = download_update(
            url,
            on_progress=lambda done, total: _set_status(
                f"Downloading... {done // 1024 // 1024}MB / {total // 1024 // 1024}MB"
            ),
        )
        if path:
            _set_status(f"Downloaded to {path}")
            update_state["downloading"] = False
            _refresh_ui()
        else:
            _set_status("Download failed")

    threading.Thread(target=work, daemon=True).start()


def _refresh_ui() -> None:
    s = update_state
    if s["checking"] or _update_label is None or _update_btn is None:
        return

    if s["error"]:
        _update_label.set_text(f"⚠ {s['error']}")
        _update_btn.set_text("Retry")
        _update_btn.on("click", _do_check, once=False)  # type: ignore[call-arg]
        return

    if s["available"]:
        size_mb = s["size"] / 1_048_576 if s["size"] else 0
        if s["download_url"]:
            _update_label.set_text(f"v{s['latest_version']} available ({size_mb:.0f} MB)")
            _update_btn.set_text("Download")
            _update_btn.on("click", _do_download, once=False)  # type: ignore[call-arg]
        else:
            _update_label.set_text(f"v{s['latest_version']} available — download from GitHub")
            _update_btn.set_text("Open Releases")
            _update_btn.on("click", lambda: ui.open(s["release_url"]), once=False)  # type: ignore[call-arg, operator]
        return

    _update_label.set_text(f"v{__version__} (up to date)")
    _update_btn.set_text("Check Again")
    _update_btn.on("click", _do_check, once=False)  # type: ignore[call-arg]


def create() -> None:
    global _update_label, _update_btn

    with ui.card().classes("w-full"):
        with ui.row().classes("items-center justify-between w-full"):
            ui.markdown("## About").classes("q-mb-none")
            with ui.row().classes("items-center gap-2"):
                ui.badge(f"v{__version__}", color="primary")

        ui.markdown("""
**Supplier Scraper** — A Google-based supplier and medical device manufacturer data extraction tool.

Built with [NiceGUI](https://nicegui.io), packaged with [PyInstaller](https://pyinstaller.org).

---

### Updates

""")

        _update_label = ui.label("").classes("text-body2")
        _update_btn = ui.button("Check for Updates", on_click=_do_check).props("outline")

        _do_check()

    with ui.card().classes("w-full"):
        ui.markdown("""
## How to Use

1. **Configuration** — Go to the Configuration tab and enter your search queries (one per line). The defaults are pre-filled for CSSD/sterilization suppliers in Africa.

2. **Start** — Go to the Run tab and click **Start Scraping**. A Chrome browser window will open automatically — do not close or minimize it.

3. **CAPTCHA** — If Google asks you to verify you're human, solve the CAPTCHA in the browser window. The scraper will detect when it's solved and resume automatically.

4. **Progress** — Results appear live in the table as they are collected. You can monitor progress in the log output.

5. **Download** — When complete, click **Download Excel** to save the results.

### What Gets Extracted

For each company found, the scraper collects: Company Name, Contact Person, Position, State, City, Country, Phone Number, Email, Website, and Products.

### Troubleshooting

- **"No Chrome found"** — The scraper will automatically download Chrome for Testing on first run (one-time, ~200MB).
- **CAPTCHA timeout** — If a CAPTCHA isn't solved within 5 minutes, the scraper will stop. Restart and try again.
- **Cancel** — Click **Cancel** to stop scraping mid-way. The scraper will finish its current task and shut down gracefully. Results collected so far will be saved to the output file. The button shows a spinner while shutting down. After cancellation, you can modify the configuration and start again.
""")
