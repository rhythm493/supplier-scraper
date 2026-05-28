from __future__ import annotations

import hashlib
import json
import tempfile
import threading
from typing import Any

import gradio as gr
import pandas as pd

from gui.utils import (
    COLUMNS,
    DEFAULT_CONTACT_KEYWORDS,
    DEFAULT_COUNTRIES,
    DEFAULT_COUNTRY_KEYWORDS,
    DEFAULT_ECOMMERCE_INDICATORS,
    DEFAULT_EXCLUDED_SITES,
    DEFAULT_PHONE_PATTERNS,
    DEFAULT_PHONE_PREFIXES,
    DEFAULT_PRODUCT_CATEGORIES,
    DEFAULT_SEARCH_QUERIES,
    State,
    build_config,
    make_initial_state,
    patch_captcha_handler,
    scraper_worker,
)

_APP_CSS = """
.log-box {
    background: #1e1e1e;
    color: #d4d4d4;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 12px;
    line-height: 1.4;
    padding: 8px 12px;
    border-radius: 6px;
    height: 100px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
    resize: none;
    margin: 0;
    border: 1px solid #333;
}
.log-box::-webkit-scrollbar { width: 8px; }
.log-box::-webkit-scrollbar-track { background: #2a2a2a; }
.log-box::-webkit-scrollbar-thumb { background: #555; border-radius: 4px; }
footer { display: none !important; }
"""


def _df_hash(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return ""
    return hashlib.md5(pd.util.hash_pandas_object(df).to_numpy().tobytes()).hexdigest()


def _run_scrape(
    queries_text: str,
    excluded_text: str,
    categories_text: str,
    countries_text: str,
    country_keywords_text: str,
    contact_keywords_text: str,
    ecom_text: str,
    phone_prefixes_text: str,
    phone_patterns_text: str,
    output_filename: str,
    max_pages: int,
    max_attempts: int,
    timeout: int,
    screenshots: bool,
    global_state: State,
) -> Any:
    search_queries = [q.strip() for q in queries_text.strip().split("\n") if q.strip()]
    excluded_sites = [s.strip() for s in excluded_text.strip().split("\n") if s.strip()]
    product_categories = [c.strip() for c in categories_text.strip().split("\n") if c.strip()]
    countries = [c.strip() for c in countries_text.strip().split("\n") if c.strip()]
    country_keywords = [k.strip() for k in country_keywords_text.strip().split("\n") if k.strip()]
    contact_keywords = [k.strip() for k in contact_keywords_text.strip().split("\n") if k.strip()]
    ecommerce_indicators = [e.strip() for e in ecom_text.strip().split("\n") if e.strip()]
    phone_prefixes = [p.strip() for p in phone_prefixes_text.strip().split("\n") if p.strip()]
    phone_patterns = [p.strip() for p in phone_patterns_text.strip().split("\n") if p.strip()]

    if not search_queries:
        raise gr.Error("At least one search query is required")

    config = build_config(
        search_queries=search_queries,
        excluded_sites=excluded_sites,
        product_categories=product_categories,
        contact_keywords=contact_keywords,
        countries=countries,
        country_keywords=country_keywords,
        phone_prefixes=phone_prefixes,
        phone_patterns=phone_patterns,
        ecommerce_indicators=ecommerce_indicators,
        output_filename=output_filename,
        max_search_pages=int(max_pages),
        max_search_attempts=int(max_attempts),
        page_load_timeout=int(timeout),
        screenshots=screenshots,
    )

    cancel_event = threading.Event()
    scrape_state = make_initial_state()
    global_state["cancel_event"] = cancel_event

    patch_captcha_handler(scrape_state)

    thread = threading.Thread(
        target=scraper_worker,
        args=(config, scrape_state, cancel_event),
        daemon=True,
    )
    thread.start()

    prev_log = ""
    prev_df_h = ""

    yield (
        "▶ **Starting...**",
        gr.update(visible=False),
        "",
        pd.DataFrame(columns=COLUMNS),
        gr.update(visible=False),
    )

    while thread.is_alive():
        status = scrape_state.get("phase", "Running...")
        captcha = scrape_state.get("captcha", False)
        log_lines = scrape_state.get("log", [])
        log_text = "\n".join(log_lines[-5:])
        df = scrape_state.get("df")
        if df is None or df.empty:
            df = pd.DataFrame(columns=COLUMNS)

        updated: dict[str, Any] = {}
        updated["status"] = f"▶ **{status}**"

        if captcha:
            updated["captcha"] = gr.update(
                visible=True,
                value="⚠ **CAPTCHA DETECTED** — Switch to the Chrome browser window and solve it. "
                "The scraper will resume automatically once solved.",
            )
        else:
            updated["captcha"] = gr.update(visible=False)

        if log_text != prev_log:
            prev_log = log_text
            escaped = log_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            updated["log"] = f'<div class="log-box">{escaped}</div>'

        current_h = _df_hash(df)
        if current_h != prev_df_h:
            prev_df_h = current_h
            updated["df"] = df

        output_file_upd = gr.update(visible=False)
        updated["output_file"] = output_file_upd

        yield (
            updated["status"],
            updated["captcha"],
            updated.get("log", gr.skip()),
            updated.get("df", gr.skip()),
            updated["output_file"],
        )

    if scrape_state.get("error"):
        error_msg = scrape_state["error"]
        log_lines = scrape_state.get("log", [])
        log_text = "\n".join(log_lines[-5:])
        escaped = log_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        df = scrape_state.get("df")
        if df is None or df.empty:
            df = pd.DataFrame(columns=COLUMNS)
        yield (
            f"❌ **Error:** {error_msg}",
            gr.update(visible=False),
            f'<div class="log-box">{escaped}</div>',
            df,
            gr.update(visible=False),
        )
    else:
        df = scrape_state.get("df", pd.DataFrame(columns=COLUMNS))
        output_path = scrape_state.get("output_path")
        log_text = "\n".join(scrape_state.get("log", [])[-5:])
        escaped = log_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        yield (
            f"✅ **Complete!** Found {len(df)} companies.",
            gr.update(visible=False),
            f'<div class="log-box">{escaped}</div>',
            df,
            gr.update(visible=output_path is not None, value=output_path) if output_path else gr.update(visible=False),
        )

    if scrape_state.get("error"):
        error_msg = scrape_state["error"]
        log_lines = scrape_state.get("log", [])
        log_text = "\n".join(log_lines[-5:])
        escaped = log_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        df = scrape_state.get("df")
        if df is None or df.empty:
            df = pd.DataFrame(columns=COLUMNS)
        yield (
            f"❌ **Error:** {error_msg}",
            gr.update(visible=False),
            f'<div class="log-box">{escaped}</div>',
            df,
            gr.update(visible=False),
        )
    else:
        df = scrape_state.get("df", pd.DataFrame(columns=COLUMNS))
        output_path = scrape_state.get("output_path")
        log_text = "\n".join(scrape_state.get("log", [])[-40:])
        escaped = log_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        yield (
            f"✅ **Complete!** Found {len(df)} companies. Click Download to save.",
            gr.update(visible=False),
            f'<div class="log-box">{escaped}</div>',
            df,
            gr.update(visible=output_path is not None, value=output_path) if output_path else gr.update(visible=False),
        )


def _do_cancel(global_state: State) -> None:
    cancel_event = global_state.get("cancel_event")
    if cancel_event is not None:
        cancel_event.set()


def _join_lines(items: list[str]) -> str:
    return "\n".join(items) if items else ""


def _import_config(file: Any) -> tuple:
    try:
        with open(file.name) as f:
            cfg = json.load(f)
        return (
            _join_lines(cfg.get("search_queries", DEFAULT_SEARCH_QUERIES)),
            _join_lines(cfg.get("excluded_sites", DEFAULT_EXCLUDED_SITES)),
            _join_lines(cfg.get("product_categories", DEFAULT_PRODUCT_CATEGORIES)),
            _join_lines(cfg.get("countries", DEFAULT_COUNTRIES)),
            _join_lines(cfg.get("country_keywords", DEFAULT_COUNTRY_KEYWORDS)),
            _join_lines(cfg.get("contact_keywords", DEFAULT_CONTACT_KEYWORDS)),
            _join_lines(cfg.get("ecommerce_indicators", DEFAULT_ECOMMERCE_INDICATORS)),
            _join_lines(cfg.get("phone_prefixes", DEFAULT_PHONE_PREFIXES)),
            _join_lines(cfg.get("phone_patterns", DEFAULT_PHONE_PATTERNS)),
            cfg.get("output_filename", "suppliers.xlsx"),
            int(cfg.get("max_search_pages", 5)),
            int(cfg.get("max_search_attempts", 5)),
            int(cfg.get("page_load_timeout", 15)),
            bool(cfg.get("screenshots", False)),
        )
    except Exception:
        raise gr.Error("Failed to parse config file. Ensure it is valid JSON.")


def _export_config(
    queries_text: str,
    excluded_text: str,
    categories_text: str,
    countries_text: str,
    country_keywords_text: str,
    contact_keywords_text: str,
    ecom_text: str,
    phone_prefixes_text: str,
    phone_patterns_text: str,
    output_filename: str,
    max_pages: int,
    max_attempts: int,
    timeout: int,
    screenshots: bool,
) -> str | None:
    cfg = {
        "search_queries": [q.strip() for q in queries_text.strip().split("\n") if q.strip()],
        "excluded_sites": [s.strip() for s in excluded_text.strip().split("\n") if s.strip()],
        "product_categories": [c.strip() for c in categories_text.strip().split("\n") if c.strip()],
        "countries": [c.strip() for c in countries_text.strip().split("\n") if c.strip()],
        "country_keywords": [k.strip() for k in country_keywords_text.strip().split("\n") if k.strip()],
        "contact_keywords": [k.strip() for k in contact_keywords_text.strip().split("\n") if k.strip()],
        "ecommerce_indicators": [e.strip() for e in ecom_text.strip().split("\n") if e.strip()],
        "phone_prefixes": [p.strip() for p in phone_prefixes_text.strip().split("\n") if p.strip()],
        "phone_patterns": [p.strip() for p in phone_patterns_text.strip().split("\n") if p.strip()],
        "output_filename": output_filename,
        "max_search_pages": int(max_pages),
        "max_search_attempts": int(max_attempts),
        "page_load_timeout": int(timeout),
        "screenshots": bool(screenshots),
    }
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, prefix="scraper_config_")
    json.dump(cfg, tmp, indent=2)
    tmp.close()
    return tmp.name


def create_ui() -> gr.Blocks:
    _DEFAULT_QUERIES_STR = "\n".join(DEFAULT_SEARCH_QUERIES)
    _DEFAULT_EXCLUDED_STR = "\n".join(DEFAULT_EXCLUDED_SITES)
    _DEFAULT_CATEGORIES_STR = "\n".join(DEFAULT_PRODUCT_CATEGORIES)
    _DEFAULT_COUNTRIES_STR = "\n".join(DEFAULT_COUNTRIES)
    _DEFAULT_COUNTRY_KW_STR = "\n".join(DEFAULT_COUNTRY_KEYWORDS)
    _DEFAULT_CONTACT_KW_STR = "\n".join(DEFAULT_CONTACT_KEYWORDS)
    _DEFAULT_ECOM_STR = "\n".join(DEFAULT_ECOMMERCE_INDICATORS)
    _DEFAULT_PREFIXES_STR = "\n".join(DEFAULT_PHONE_PREFIXES)
    _DEFAULT_PATTERNS_STR = "\n".join(DEFAULT_PHONE_PATTERNS)

    with gr.Blocks(
        title="Supplier Scraper",
        fill_height=True,
        css=_APP_CSS,
    ) as app:
        gr.Markdown("# 🏭 Supplier Scraper")
        gr.Markdown("Extract supplier and manufacturer data from Google Search results.")

        global_state = gr.State(make_initial_state())

        with gr.Tabs():
            with gr.TabItem("⚙ Configuration"):
                with gr.Group():
                    gr.Markdown("### Search Settings")
                    queries_text = gr.Textbox(
                        label="Search Queries (one per line)",
                        lines=6,
                        value=_DEFAULT_QUERIES_STR,
                        placeholder="CSSD distributor in Africa\nSterilization pouches supplier...",
                    )
                    excluded_text = gr.Textbox(
                        label="Excluded Sites (one per line) — partial match, lowercase",
                        lines=4,
                        value=_DEFAULT_EXCLUDED_STR,
                    )

                    with gr.Row():
                        max_pages = gr.Slider(label="Max Search Pages", value=5, minimum=1, maximum=20, step=1)
                        max_attempts = gr.Slider(label="Max Search Attempts", value=5, minimum=1, maximum=10, step=1)
                        timeout = gr.Slider(label="Page Load Timeout (s)", value=15, minimum=5, maximum=60, step=5)

                with gr.Group():
                    gr.Markdown("### Filtering")
                    categories_text = gr.Textbox(
                        label="Product Categories (one per line)",
                        lines=5,
                        value=_DEFAULT_CATEGORIES_STR,
                    )
                    countries_text = gr.Textbox(
                        label="Target Countries (one per line)",
                        lines=4,
                        value=_DEFAULT_COUNTRIES_STR,
                    )
                    country_keywords_text = gr.Textbox(
                        label="Country Keywords (one per line)",
                        lines=2,
                        value=_DEFAULT_COUNTRY_KW_STR,
                    )

                with gr.Row():
                    output_filename = gr.Textbox(label="Output Filename", value="suppliers.xlsx", scale=3)
                    screenshots = gr.Checkbox(label="Take Screenshots", value=False, scale=1)

                with gr.Accordion("🔧 Advanced Settings", open=False):
                    contact_keywords_text = gr.Textbox(
                        label="Contact Page Keywords",
                        lines=2,
                        value=_DEFAULT_CONTACT_KW_STR,
                    )
                    ecom_text = gr.Textbox(
                        label="E-commerce Indicators (one per line)",
                        lines=4,
                        value=_DEFAULT_ECOM_STR,
                    )
                    phone_prefixes_text = gr.Textbox(
                        label="Phone Prefixes (one per line)",
                        lines=5,
                        value=_DEFAULT_PREFIXES_STR,
                    )
                    phone_patterns_text = gr.Textbox(
                        label="Phone Regex Patterns (one per line)",
                        lines=3,
                        value=_DEFAULT_PATTERNS_STR,
                    )

                with gr.Row():
                    import_btn = gr.UploadButton("📂 Import Config", file_types=[".json"], scale=1)
                    export_btn = gr.DownloadButton("💾 Export Config", scale=1)
                    gr.ClearButton(
                        components=[
                            queries_text,
                            excluded_text,
                            categories_text,
                            countries_text,
                            country_keywords_text,
                            contact_keywords_text,
                            ecom_text,
                            phone_prefixes_text,
                            phone_patterns_text,
                            output_filename,
                            max_pages,
                            max_attempts,
                            timeout,
                            screenshots,
                        ],
                        value="↺ Reset Defaults",
                        scale=1,
                    )

            with gr.TabItem("▶ Run"):
                status_md = gr.Markdown("**Status:** Ready. Configure your search and click **Start Scraping**.")
                captcha_md = gr.Markdown(visible=False)

                log_html = gr.HTML(
                    value='<div class="log-box">Log output will appear here...</div>',
                )

                results_df = gr.Dataframe(
                    label="Live Results",
                    interactive=False,
                    wrap=True,
                )

                with gr.Row():
                    start_btn = gr.Button("▶ Start Scraping", variant="primary", scale=2)
                    cancel_btn = gr.Button("■ Cancel", variant="stop", scale=1)

                output_file = gr.File(
                    label="📥 Download Excel",
                    visible=False,
                )

            with gr.TabItem("❓ Help"):
                gr.Markdown("""
                ## How to Use

                1. **Configuration** — Go to the Configuration tab and enter your search queries
                   (one per line). The defaults are pre-filled for CSSD/sterilization suppliers in
                   Africa.

                2. **Start** — Go to the Run tab and click **Start Scraping**. A Chrome browser
                   window will open automatically — **do not close or minimize it**.

                3. **CAPTCHA** — If Google asks you to verify you're human, solve the CAPTCHA in
                   the browser window. The scraper will detect when it's solved and resume
                   automatically.

                4. **Progress** — Results appear live in the table as they are collected. You can
                   monitor progress in the log output.

                5. **Download** — When complete, click **Download Excel** to save the results.

                ### What Gets Extracted

                For each company found, the scraper collects: Company Name, Contact Person,
                Position, State, City, Country, Phone Number, Email, Website, and Products.

                ### Troubleshooting

                - **"No Chrome found"** — The scraper will automatically download Chrome for
                  Testing on first run (one-time, ~200MB).
                - **CAPTCHA timeout** — If a CAPTCHA isn't solved within 5 minutes, the scraper
                  will stop. Restart and try again.
                - **Cancel** — Click Cancel to stop scraping mid-way. Results collected so far
                  will be saved.
                """)

        inputs = [
            queries_text,
            excluded_text,
            categories_text,
            countries_text,
            country_keywords_text,
            contact_keywords_text,
            ecom_text,
            phone_prefixes_text,
            phone_patterns_text,
            output_filename,
            max_pages,
            max_attempts,
            timeout,
            screenshots,
            global_state,
        ]
        outputs = [status_md, captcha_md, log_html, results_df, output_file]

        event = start_btn.click(
            fn=_run_scrape,
            inputs=inputs,
            outputs=outputs,
            stream_every=0.5,  # type: ignore[call-arg]
            show_progress="hidden",  # type: ignore[call-arg]
        )

        cancel_btn.click(
            fn=_do_cancel,
            inputs=[global_state],
            cancels=[event],
        )

        import_inputs = [
            queries_text,
            excluded_text,
            categories_text,
            countries_text,
            country_keywords_text,
            contact_keywords_text,
            ecom_text,
            phone_prefixes_text,
            phone_patterns_text,
            output_filename,
            max_pages,
            max_attempts,
            timeout,
            screenshots,
        ]

        import_btn.upload(
            fn=_import_config,
            inputs=import_btn,
            outputs=import_inputs,
        )

        export_inputs = [
            queries_text,
            excluded_text,
            categories_text,
            countries_text,
            country_keywords_text,
            contact_keywords_text,
            ecom_text,
            phone_prefixes_text,
            phone_patterns_text,
            output_filename,
            max_pages,
            max_attempts,
            timeout,
            screenshots,
        ]

        export_btn.click(
            fn=_export_config,
            inputs=export_inputs,
            outputs=[export_btn],
        )

    return app
