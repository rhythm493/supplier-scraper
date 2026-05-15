# Supplier Scraper

Search Google for suppliers/manufacturers, visit their websites, and extract contact info into an Excel spreadsheet.

## Quick Start

1. **Install Python 3.10+** from [python.org](https://python.org)

2. **Open a terminal** in this folder and install dependencies:
   ```bash
   pip install -r scraper/requirements.txt
   ```

3. **Launch Jupyter:**
   ```bash
   jupyter notebook Supplier_Scraper.ipynb
   ```

4. **Run the cells in order:**
   - **Cell 0** — Installs any remaining dependencies, downloads Chrome
   - **Cell 1** — Edit your search settings (queries, countries, products, etc.)
   - **Cell 2** — Runs the scraper. A progress bar shows live results.

5. **Get your output** — the `.xlsx` file appears in the same folder.

## Output Columns

Company Name | Contact Person | Position | State | City | Country | Phone Number | Email | Website | Products

## Need Help?

Copy Cell 1 to ChatGPT and describe what you're looking for — it will generate the right config for you.
