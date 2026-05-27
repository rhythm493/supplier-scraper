# Supplier Scraper

Search Google for suppliers/manufacturers, visit their websites, and extract contact info into an Excel spreadsheet.

## Quick Start

1. **Install Python 3.10+** from [python.org](https://python.org)

2. **Open a terminal** in this folder and install dependencies:
   ```bash
   pip install -e .
   ```

3. **Launch the GUI:**
   ```bash
   python run_scraper.py
   ```
   A browser window will open with the configuration interface.  
   *Alternatively, run in Jupyter: `jupyter notebook Supplier_Scraper.ipynb`*

4. **Configure & Run:**
   - **Configuration tab** — Set search queries, countries, products to filter, etc.
   - **Run tab** — Click **Start** to begin scraping. Progress, results, and logs update live.
   - **Help tab** — Reference for all fields.

5. **Get your output** — the `.xlsx` file appears in the same folder.

## Output Columns

Company Name | Contact Person | Position | State | City | Country | Phone Number | Email | Website | Products

## Need Help?

Copy Cell 1 to ChatGPT and describe what you're looking for — it will generate the right config for you.
