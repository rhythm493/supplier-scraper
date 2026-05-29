# Patchright Migration Plan

## Summary
Migrate from `undetected-chromedriver` (Selenium-based) to `patchright` (Playwright-based, stealth-patched). Drops selenium, undetected-chromedriver, webdriver-manager dependencies. Cuts browser.py from 308 to ~50 lines. Phase 2 goes from 4 Chrome processes to 1 browser + 4 contexts (~75% memory reduction).

## Dependency Changes

| Before | After |
|--------|-------|
| selenium==4.44.0 | **removed** |
| undetected-chromedriver==3.5.5 | **removed** |
| webdriver-manager==4.1.1 | **removed** |
| | **+** patchright>=1.60.0 |

## File-by-File Changes

### 1. `pyproject.toml`
- Swap 3 deps for 1
- Remove `undetected-chromedriver` type ignore from mypy config (no longer needed)

### 2. `scraper/browser.py` — Complete Rewrite (308 → ~45 lines)

**Delete**: Everything. All 17 functions.

**Write**: 
- `setup_page(url: str, page_load_timeout: int = 25) -> Page`
  - Launches `sync_playwright().start()`, opens `chromium.launch_persistent_context(channel="chrome", headless=False, no_viewport=True)`, creates `context.new_page()`
  - Sets `page.set_default_timeout(page_load_timeout * 1000)`
  - Adds network route blocking: `page.route("**/*.{png,jpg,jpeg,gif,svg,css}", lambda r: r.abort())`
  - Returns page
- `close_page(page: Page)` — Closes context and browser
- Module-level `_playwright` singleton for REPL/context-manager-free usage

### 3. `scraper/search.py` — API Translation (~440 → ~340 lines)

Type annotation changes only:
- `driver: Chrome` → `page: Page` (from `patchright.sync_api`)
- Import changes: remove selenium, keep BS4, add `patchright.sync_api` for `Page`

Function changes:
| Function | Change |
|----------|--------|
| `google_search(page, query, config)` | `page` type, `page.goto()` replaces `driver.get()`, `page.context.clear_cookies()` replaces `driver.delete_all_cookies()` |
| `detect_captcha(page)` | `page.content()` replaces `driver.page_source`. `page.locator("iframe")` + `.get_attribute("src")` replaces `driver.find_elements(By.TAG_NAME, "iframe")` |
| `wait_for_captcha(page, ...)` | Same logic, `page.content()` for detection |
| `_human_scroll(page)` | `page.mouse.wheel(0, delta)` replaces `ActionChains.scroll_by_amount` |
| `_handle_consent_popup(page)` | `page.locator("button:has-text('Accept')")` + auto-wait click — no WebDriverWait needed |
| `_type_and_search(page, query)` | `page.locator('[name="q"]').press_sequentially(query, delay=50)` replaces character-by-character loop |
| `_save_screenshot(page, ...)` | `page.screenshot(path=path)` replaces `driver.save_screenshot()` |
| `_extract_search_results(page, ...)` | `page.content()` for HTML, BS4 same. **Remove** `_selenium_fallback` entirely — BS4 CSS selectors handle all cases now |
| `_navigate_next_page(page)` | `page.locator("a#pnnext").click()` with auto-wait. Fallback URL construction same. No `EC.staleness_of` needed — Playwright auto-waits |

### 4. `scraper/pipeline.py` (~279 → ~230 lines)

- `driver: Chrome` → `page: Page`
- `page.goto(url, wait_until="domcontentloaded")` replaces `driver.get()` + `WebDriverWait(body)` + `time.sleep()`
- `page.content()` replaces `driver.page_source`
- `page.locator(xpath).element_handles()` replaces `driver.find_elements("xpath", pat)`
- `page.evaluate(fetch_head_js)` for HEAD request in `_find_page` — same mechanic
- Remove selenium imports. Keep BS4, requests

### 5. `scraper/runner.py` (~342 → ~300 lines)

Biggest conceptual change:

**Phase 1 (search)**: Replace `setup_driver()` + `driver.quit()` with:
```python
from patchright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=False)
    page = browser.new_page()
    # ... google_search(page, query, config) ...
```

**Phase 2 (parallel visits)**: Replace `_process_chunk` creating its own `setup_driver()` with:
```python
browser = p.chromium.launch(channel="chrome", headless=False)
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {
        executor.submit(_process_chunk, chunk, config, wid, browser): wid
    }
browser.close()
```

`_process_chunk(browser)`:
```python
context = browser.new_context()
page = context.new_page()
# ... extract_company_info(page, ...) ...
context.close()
```

### 6. `gui/utils.py` (~305 lines, annotions only)
- No functional changes
- `patch_captcha_handler` works the same — `search_module.wait_for_captcha` signature unchanged (still takes `page`, original type was `Chrome`)

### 7. Build files
- `build/scraper.spec`: Remove selenium/uc/wdm hidden imports. Add `patchright` (has built-in PyInstaller hook at `patchright/_impl/__pyinstaller/`)
- `build/build.sh`: Add `patchright install chrome` step before pyinstaller

## What Improves
- **~75% memory reduction** in Phase 2 (1 browser + 4 contexts vs 4 separate browsers)
- **Auto-waiting**: No more WebDriverWait, EC, explicit waits for element presence
- **Better stealth**: patchright patches CDP leaks that undetected-chromedriver can't
- **Removes 17 functions**: All of browser.py's platform detection, CfT download, fallback logic
- **Smaller deps**: 3 packages → 1

## What Stays the Same
- BS4 extraction logic (email, phone, country, products)
- CAPTCHA detection/waiting (same text indicators and polling)
- Search cache (JSON save/load)
- Config, types, extractors, validators, dedup modules
- GUI (app.py, utils.py state management)
- Excel output formatting
