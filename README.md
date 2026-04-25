# Flipkart Product Scraper

## What This Project Does
This project scrapes product information from a Flipkart product page and saves data in multiple formats.

It is designed to handle anti-bot pages by using a two-step strategy:
- Try normal HTTP request first.
- If blocked, open a real Chrome browser and continue after manual verification.

## What I Built
I implemented a practical scraper workflow that:
- Fetches a product page from Flipkart.
- Detects captcha or human-verification responses.
- Falls back to Selenium browser mode when needed.
- Avoids overwriting saved HTML with captcha HTML.
- Extracts structured product data from JSON-LD and HTML content.
- Saves clean output files for later use.

## Main Script
- Retrieving_html.py

## Output Files
After a successful run, the script saves:
- flipkart.html: Raw product page HTML snapshot.
- product_data.json: Full structured product data.
- product_data.csv: Flat summary (single row) with key product fields.
- product_specs.csv: Specification key-value pairs.

## Libraries Used
### External libraries
- requests
- beautifulsoup4
- selenium

### Python standard library modules
- os
- random
- re
- time
- json
- csv
- urllib.parse

## How the Script Works
1. Build realistic browser-like headers.
2. Send request with retries.
3. Detect captcha using keywords such as:
   - are you a human
   - recaptcha
4. If blocked, open Chrome using Selenium.
5. You manually complete verification if needed.
6. Script captures page source and, if required, retries with browser cookies.
7. Script saves HTML only when response is not captcha.
8. Script parses product fields and writes JSON/CSV outputs.

## Data Extracted
From structured JSON-LD and page metadata/specs, the script attempts to capture:
- Product name
- Price
- Description
- SKU
- Brand
- Color
- Category
- Availability
- Rating value
- Rating count
- Review count
- Offers data
- Product images
- Reviews (when available)
- Specifications (table-based and fallback highlights)
- Canonical URL and meta fields

## Installation
Create and activate a virtual environment (recommended), then install dependencies.

Windows PowerShell example:

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install requests beautifulsoup4 selenium

## Run
From the project folder:

python Retrieving_html.py

If your environment uses a specific Python path, run with that interpreter.

## Important Behavior Explained
### Why Chrome opens but no captcha appears
This is normal. Sometimes Flipkart allows the session directly, so captcha is not shown.

### Why opening local flipkart.html may show Oops! Something broke
Also normal. The saved HTML is a static snapshot and may depend on live Flipkart scripts, APIs, and session context. Running it locally cannot fully reproduce the live site behavior.

Use product_data.json, product_data.csv, and product_specs.csv as the reliable outputs instead of checking local page rendering.

## Troubleshooting
### Problem: Script keeps getting captcha page
- Let browser fallback open and complete verification.
- Press Enter only after product details are clearly visible.
- Optionally pass cookie string through environment variable:

PowerShell:
$env:FLIPKART_COOKIE="cookie_name=cookie_value; other_cookie=other_value"
python Retrieving_html.py

### Problem: Browser fallback unavailable
Install Selenium:
- pip install selenium

### Problem: Price says Not found
The parser already includes JSON-LD and fallback matching. Re-run after a successful non-captcha capture to refresh HTML.

## Notes and Limitations
- Flipkart markup and anti-bot behavior can change at any time.
- Selectors and extraction logic may need periodic updates.
- This project includes a manual step for human verification when required.

## Suggested Next Improvements
- Add timestamped output files per run.
- Add support for multiple product URLs from a text file or CSV.
- Add logging and error reports.
- Add unit tests for parser functions.
