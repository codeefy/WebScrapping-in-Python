import os
import random
import re
import time
import json
import csv
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
except ImportError:
    webdriver = None
    Options = None

URL = "https://www.flipkart.com/apple-iphone-17-pro-silver-256-gb/p/itm106f475c264c7?pid=MOBHFN6YPFSDYRTY&lid=LSTMOBHFN6YPFSDYRTYSCL89I&hl_lid=&marketplace=FLIPKART&fm=eyJ3dHAiOiJwbXVfdjIiLCJwcnB0IjoiaHAiLCJtaWQiOiJjb250aW51dW0vaHAifQ%3D%3D&pageUID=1777110860582"
OUTPUT_FILE = "flipkart.html"
OUTPUT_JSON = "product_data.json"
OUTPUT_CSV = "product_data.csv"
OUTPUT_SPECS_CSV = "product_specs.csv"


def build_headers() -> dict:
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
        "Referer": "https://www.flipkart.com/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }


def looks_like_captcha(html: str) -> bool:
    check_text = html.lower()
    markers = [
        "are you a human",
        "recaptcha",
        "flipkart recaptcha",
        "confirming...",
    ]
    return any(marker in check_text for marker in markers)


def save_html(content: str, file_name: str = OUTPUT_FILE) -> None:
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(content)


def safe_get(data: dict, path: list, default=None):
    current = data
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def parse_product_data(html: str, source_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    metadata = {
        "source_url": source_url,
        "canonical_url": "",
        "meta_title": "",
        "meta_description": "",
        "meta_keywords": "",
    }

    canonical = soup.select_one("link[rel='canonical']")
    if canonical and canonical.get("href"):
        metadata["canonical_url"] = canonical["href"]

    title_tag = soup.select_one("title")
    if title_tag:
        metadata["meta_title"] = title_tag.get_text(strip=True)

    desc_tag = soup.select_one("meta[name='Description'], meta[name='description']")
    if desc_tag and desc_tag.get("content"):
        metadata["meta_description"] = desc_tag["content"].strip()

    keywords_tag = soup.select_one("meta[name='Keywords'], meta[name='keywords']")
    if keywords_tag and keywords_tag.get("content"):
        metadata["meta_keywords"] = keywords_tag["content"].strip()

    product = {
        "name": "",
        "description": "",
        "sku": "",
        "color": "",
        "category": "",
        "brand": "",
        "images": [],
        "offers": {},
        "aggregate_rating": {},
        "reviews": [],
    }

    json_ld_tag = soup.select_one("script#jsonLD")
    if json_ld_tag and json_ld_tag.string:
        try:
            payload = json.loads(json_ld_tag.string)
            entries = payload if isinstance(payload, list) else [payload]

            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                if safe_get(entry, ["@type"]) and str(entry.get("@type")).lower() not in {"product", ""}:
                    continue

                product["name"] = entry.get("name", "")
                product["description"] = entry.get("description", "")
                product["sku"] = entry.get("sku", "")
                product["color"] = entry.get("color", "")
                product["category"] = entry.get("category", "")
                product["brand"] = safe_get(entry, ["brand", "name"], "")
                product["images"] = entry.get("image", []) if isinstance(entry.get("image", []), list) else []
                product["offers"] = entry.get("offers", {}) if isinstance(entry.get("offers"), dict) else {}
                product["aggregate_rating"] = entry.get("aggregateRating", {}) if isinstance(entry.get("aggregateRating"), dict) else {}
                product["reviews"] = entry.get("review", []) if isinstance(entry.get("review"), list) else []
                break
        except json.JSONDecodeError:
            pass

    specs = {}
    for table in soup.select("table"):
        for row in table.select("tr"):
            cells = row.select("td")
            if len(cells) >= 2:
                key = cells[0].get_text(" ", strip=True)
                value = cells[1].get_text(" ", strip=True)
                if key and value and key not in specs:
                    specs[key] = value

    if not specs:
        # Fallback for non-table spec layouts.
        key_texts = [
            node.get_text(" ", strip=True)
            for node in soup.select("[class*='spec'], [class*='Spec'], [class*='highlight'], [class*='Highlight']")
        ]
        # Keep short informative lines only.
        highlights = [line for line in key_texts if 2 <= len(line) <= 120]
        if highlights:
            specs["highlights"] = "; ".join(dict.fromkeys(highlights[:20]))

    price_display = ""
    offer_price = product["offers"].get("price") if isinstance(product["offers"], dict) else None
    if offer_price is not None:
        try:
            price_display = f"Rs. {int(float(offer_price)):,}"
        except (TypeError, ValueError):
            price_display = str(offer_price)

    if not price_display:
        rupee_matches = re.findall(r"₹\s?\d[\d,]*", html)
        if rupee_matches:
            price_display = rupee_matches[0]

    return {
        "metadata": metadata,
        "product": product,
        "specifications": specs,
        "summary": {
            "title": product.get("name") or metadata.get("meta_title", ""),
            "price": price_display or "Not found",
            "rating_value": safe_get(product, ["aggregate_rating", "ratingValue"], ""),
            "rating_count": safe_get(product, ["aggregate_rating", "ratingCount"], ""),
            "review_count": safe_get(product, ["aggregate_rating", "reviewCount"], ""),
            "availability": safe_get(product, ["offers", "availability"], ""),
            "sku": product.get("sku", ""),
            "brand": product.get("brand", ""),
            "color": product.get("color", ""),
            "category": product.get("category", ""),
        },
    }


def save_product_data(product_data: dict) -> None:
    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(product_data, file, ensure_ascii=False, indent=2)

    summary = product_data.get("summary", {})
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)

    specs = product_data.get("specifications", {})
    with open(OUTPUT_SPECS_CSV, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["specification", "value"])
        writer.writeheader()
        for key, value in specs.items():
            writer.writerow({"specification": key, "value": value})


def parse_quick_details(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = "Not found"
    price = "Not found"

    title_tag = soup.select_one("span.B_NuCI") or soup.select_one("h1")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # Newer Flipkart layouts often expose canonical price in JSON-LD.
    json_ld_tag = soup.select_one("script#jsonLD")
    if json_ld_tag and json_ld_tag.string:
        try:
            payload = json.loads(json_ld_tag.string)
            entries = payload if isinstance(payload, list) else [payload]
            for entry in entries:
                offers = entry.get("offers", {}) if isinstance(entry, dict) else {}
                raw_price = offers.get("price")
                if raw_price is not None:
                    price_int = int(float(raw_price))
                    price = f"Rs. {price_int:,}"
                    break
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    price_tag = soup.select_one("div._30jeq3") or soup.select_one("div.Nx9bqj")
    if price_tag:
        price = price_tag.get_text(strip=True)

    if price == "Not found":
        rupee_matches = re.findall(r"₹\s?\d[\d,]*", html)
        if rupee_matches:
            price = rupee_matches[0].replace("\u20b9", "₹")

    return title, price


def fetch_product_page(url: str) -> str:
    session = requests.Session()
    session.headers.update(build_headers())

    # Optional: pass your real Flipkart browser cookie through environment variable.
    # PowerShell example:
    # $env:FLIPKART_COOKIE="cookie_name=cookie_value; other_cookie=other_value"
    cookie_from_env = os.getenv("FLIPKART_COOKIE", "").strip()
    if cookie_from_env:
        session.headers.update({"Cookie": cookie_from_env})

    for attempt in range(1, 4):
        response = session.get(url, timeout=25)
        html = response.text

        if response.status_code == 200 and not looks_like_captcha(html):
            return html

        wait_seconds = attempt * 2
        print(f"Attempt {attempt}: blocked or captcha detected. Retrying in {wait_seconds}s...")
        time.sleep(wait_seconds)

    return html


def fetch_with_browser_fallback(url: str) -> str:
    if webdriver is None or Options is None:
        print("Browser fallback unavailable. Install with: pip install selenium")
        return ""

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        print("Browser opened. If captcha appears, solve it in Chrome.")
        input("After page fully loads, press Enter here to continue...")

        browser_html = driver.page_source
        if not looks_like_captcha(browser_html):
            return browser_html

        # If DOM is still captcha, try one authenticated request using browser cookies.
        parsed = urlparse(url)
        cookie_header = "; ".join(
            f"{cookie['name']}={cookie['value']}"
            for cookie in driver.get_cookies()
            if cookie.get("name") and cookie.get("value")
        )

        session = requests.Session()
        session.headers.update(build_headers())
        session.headers.update(
            {
                "User-Agent": driver.execute_script("return navigator.userAgent") or session.headers.get("User-Agent", ""),
                "Referer": f"{parsed.scheme}://{parsed.netloc}/",
            }
        )
        if cookie_header:
            session.headers.update({"Cookie": cookie_header})

        response = session.get(url, timeout=30)
        return response.text
    finally:
        driver.quit()


def main() -> None:
    html = fetch_product_page(URL)

    if looks_like_captcha(html):
        print("Still receiving captcha page from Flipkart.")
        print("Trying browser fallback...")
        html = fetch_with_browser_fallback(URL)

    if not html:
        return

    if looks_like_captcha(html):
        print("Captcha is still present. HTML will not be overwritten.")
        print("Tip: when Chrome opens, solve captcha and confirm product details are visible before pressing Enter.")
        return

    save_html(html)

    product_data = parse_product_data(html, URL)
    save_product_data(product_data)

    title, price = parse_quick_details(html)
    print(f"Saved product page to {OUTPUT_FILE}")
    print(f"Saved structured product data to {OUTPUT_JSON}")
    print(f"Saved product summary to {OUTPUT_CSV}")
    print(f"Saved product specifications to {OUTPUT_SPECS_CSV}")
    print(f"Product title: {title}")
    print(f"Product price: {price}")


if __name__ == "__main__":
    main()


