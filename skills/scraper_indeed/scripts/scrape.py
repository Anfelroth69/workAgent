#!/usr/bin/env python3
"""
Indeed Colombia Jobs Scraper

Scrapes co.indeed.com and outputs NDJSON (one JSON object per line).
Uses Playwright for JS-rendered pages (bypasses Cloudflare).
Falls back to requests if Playwright is unavailable.

Usage:
    python3 scrape.py --keywords "call center" --location "Cali" --max-results 25
"""

import argparse
import json
import logging
import os
import sys
import time
import urllib.parse
from datetime import date
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("scraper_indeed")

try:
    import requests
except ImportError:
    log.error("requests library not installed")
    sys.exit(1)

from bs4 import BeautifulSoup

try:
    from skills.scraper_utils import playwright_fetch
except ImportError:
    try:
        import sys as _sys
        _sys.path.insert(0, "/app/skills")
        from scraper_utils import playwright_fetch
    except ImportError:
        playwright_fetch = None  # type: ignore

SEARCH_URL = "https://co.indeed.com/ofertas"
DEFAULT_RATE_LIMIT = 3.0
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "DNT": "1",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Indeed Colombia Scraper")
    parser.add_argument("--keywords", default="call center", help="Search keywords")
    parser.add_argument("--location", default="Colombia", help="City or country")
    parser.add_argument("--max-results", type=int, default=25, help="Max offers")
    return parser.parse_args()


def build_search_url(keywords: str, location: str, start: int = 0) -> str:
    params: dict[str, Any] = {"q": keywords, "l": location}
    if start > 0:
        params["start"] = start
    return f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"


def fetch_html(url: str) -> str | None:
    if playwright_fetch:
        return playwright_fetch(url, wait_selector="div.job_seen_beacon", wait_time=3)

    log.info("Playwright not available, using requests (may be blocked)")
    for attempt in range(1, 4):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200 and len(resp.text) > 500:
                return resp.text
            log.warning("Attempt %d/3: status=%d size=%d", attempt, resp.status_code, len(resp.text))
        except requests.RequestException as e:
            log.warning("Attempt %d/3 failed: %s", attempt, e)
        if attempt < 3:
            time.sleep(min(attempt * 5, 15))
    return None


def parse_offers(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    offers: list[dict] = []
    today = date.today().isoformat()

    cards = soup.select("div.job_seen_beacon")
    if not cards:
        cards = soup.select("[class*=card], div.result, table.result")
    if not cards:
        for item in soup.select("[data-jk], a[data-jk]"):
            parent = item.find_parent(["div", "li", "td"])
            if parent:
                cards.append(parent)

    for card in cards:
        try:
            offer = parse_card(card, today)
            if offer:
                offers.append(offer)
        except Exception as e:
            log.debug("Error parsing card: %s", e)

    return offers


def parse_card(card, today: str) -> dict | None:
    link_el = card.select_one(".jobTitle a, .jcs-JobTitle, a[data-jk], h2 a, h3 a")
    url = ""
    if link_el and link_el.get("href"):
        href = link_el["href"]
        if href.startswith("/"):
            url = f"https://co.indeed.com{href}"
        else:
            url = href

    title_el = card.select_one(
        ".jobTitle a, .jcs-JobTitle, span[title], "
        "a[class*=title], h2 a span, h3 a"
    )
    title = title_el.get_text(strip=True) if title_el else ""

    company_el = card.select_one(
        "div.company_location span, [data-testid=company-name], "
        "span.css-1afmp4o, span[class*=company]"
    )
    company = company_el.get_text(strip=True) if company_el else ""

    location_el = card.select_one(
        "div.company_location, [data-testid=text-location], "
        "div.css-1f06pz4, [class*=location]"
    )
    loc_text = location_el.get_text(strip=True) if location_el else ""
    location = loc_text.replace(company, "", 1).strip() if company else loc_text

    salary_el = card.select_one(
        "div.jobMetaDataGroup, [data-testid=attribute-text], "
        "span.css-zydy3i, div[class*=salary]"
    )
    salary = salary_el.get_text(strip=True) if salary_el else ""

    desc_el = card.select_one(
        "div.job-snippet, span[class*=snippet], "
        "div.summary, [class*=description], ul li"
    )
    description = desc_el.get_text(strip=True) if desc_el else ""

    date_text = today
    date_el = card.select_one("span.date, span[class*=date], .result-date")
    if date_el:
        date_text = date_el.get_text(strip=True)

    if not title and not url:
        return None

    return {
        "portal": "indeed",
        "url": url,
        "title": title,
        "company": company,
        "location": location,
        "salary": salary,
        "description": description,
        "skills_mentioned": [],
        "date_posted": date_text,
        "date_scraped": today,
    }


def scrape(keywords: str, location: str, max_results: int) -> list[dict]:
    all_offers: list[dict] = []
    start = 0

    while len(all_offers) < max_results:
        url = build_search_url(keywords, location, start)
        log.info("Fetching: keywords=%s location=%s start=%d", keywords, location, start)

        html = fetch_html(url)
        if not html:
            log.warning("Failed to fetch at start=%d", start)
            break

        offers = parse_offers(html)
        if not offers:
            log.info("No offers found at start=%d, stopping", start)
            break

        all_offers.extend(offers)
        log.info("Found %d offers (total: %d)", len(offers), len(all_offers))
        start += 10

        if len(offers) < 5:
            break

        time.sleep(DEFAULT_RATE_LIMIT)

    return all_offers[:max_results]


def main() -> None:
    args = parse_args()
    keywords = args.keywords or os.environ.get("SCRAPER_KEYWORDS", "call center")
    location = args.location or os.environ.get("SCRAPER_LOCATION", "Colombia")

    offers = scrape(keywords, location, args.max_results)
    for offer in offers:
        print(json.dumps(offer, ensure_ascii=False))

    log.info("Scraped %d offers total", len(offers))
    sys.exit(0)


if __name__ == "__main__":
    main()
