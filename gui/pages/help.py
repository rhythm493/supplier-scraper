from nicegui import ui


def create() -> None:
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
