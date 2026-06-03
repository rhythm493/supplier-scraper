from __future__ import annotations

import threading

from nicegui import ui

from gui.state import update_state
from scraper import __version__
from scraper.updater import apply_update, check_for_update, download_update


def _do_check() -> None:
    s = update_state
    if s["checking"]:
        return

    s["checking"] = True
    s["error"] = ""
    s["status_text"] = "Checking..."

    def work():
        info = check_for_update()
        s["available"] = info.available
        s["latest_version"] = info.latest_version
        s["download_url"] = info.download_url
        s["release_url"] = info.release_url
        s["asset_name"] = info.asset_name
        s["size"] = info.size
        s["error"] = info.error
        s["checking"] = False
        s["status_text"] = ""

    threading.Thread(target=work, daemon=True).start()


def _on_btn_click() -> None:
    s = update_state
    if s["checking"] or s["downloading"]:
        return
    if s["error"]:
        _do_check()
    elif s["available"]:
        if s["download_url"] and not s["download_path"]:
            _do_download()
        elif s["download_path"]:
            s["status_text"] = "Already downloaded — apply on restart"
        elif s["download_url"]:
            ui.navigate.to(s["release_url"])
        else:
            _do_check()
    else:
        _do_check()


def _do_download() -> None:
    url = update_state["download_url"]
    if not url or update_state["downloading"]:
        return

    update_state["downloading"] = True
    update_state["status_text"] = "Downloading..."
    update_state["download_path"] = ""
    update_state["applied"] = False

    def work():
        path = download_update(url)
        if path:
            update_state["download_path"] = str(path)
            applied = apply_update(path)
            if applied:
                update_state["applied"] = True
                update_state["status_text"] = "Update applied — restart to complete"
            else:
                update_state["status_text"] = "Download complete — restart to apply"
        else:
            update_state["error"] = "Download failed"
            update_state["status_text"] = ""
        update_state["downloading"] = False

    threading.Thread(target=work, daemon=True).start()


def create() -> None:
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

        update_label = ui.label("").classes("text-body2")
        update_btn = ui.button("Check for Updates", on_click=_on_btn_click).props("outline")

        def _poll():
            s = update_state

            if s["checking"]:
                update_label.set_text(s["status_text"] or "Checking...")
                update_btn.disable()
                return

            update_btn.enable()

            if s["error"]:
                update_label.set_text(f"⚠ {s['error']}")
                update_btn.set_text("Retry")
            elif s["available"]:
                size_mb = s["size"] / 1_048_576 if s["size"] else 0
                if s.get("applied"):
                    update_label.set_text("Update applied — restart to complete")
                    update_btn.set_text("Done")
                elif s["download_path"]:
                    update_label.set_text("Downloaded — restart to apply")
                    update_btn.set_text("Done")
                elif s["download_url"]:
                    update_label.set_text(f"v{s['latest_version']} available ({size_mb:.0f} MB)")
                    update_btn.set_text("Download")
                else:
                    update_label.set_text(f"v{s['latest_version']} available — download from GitHub")
                    update_btn.set_text("Open Releases")
            else:
                update_label.set_text(f"v{__version__} (up to date)")
                update_btn.set_text("Check Again")

        ui.timer(1, _poll)
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
