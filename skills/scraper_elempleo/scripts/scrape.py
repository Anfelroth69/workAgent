#!/usr/bin/env python3
"""
elempleo Colombia Jobs Scraper

Scrapes elempleo.com and outputs NDJSON (one JSON object per line).
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
log = logging.getLogger("scraper_elempleo")

try:
    import requests
except ImportError:
    log.error("requests library not available")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    log.error("BeautifulSoup not available")
    sys.exit(1)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "DNT": "1",
    "Connection": "keep-alive",
}

SEARCH_URL = "https://www.elempleo.com/co/ofertas-empleo/"
DEFAULT_RATE_LIMIT = 2.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="elempleo Colombia Scraper")
    parser.add_argument("--keywords", default="call center", help="Search keywords")
    parser.add_argument("--location", default="Colombia", help="City or country")
    parser.add_argument("--max-results", type=int, default=25, help="Max offers")
    return parser.parse_args()


def build_search_url(keywords: str, location: str) -> str:
    kw_slug = keywords.replace(",", "-").replace(" ", "-").strip("-").lower()
    loc_slug = location.replace(",", "-").replace(" ", "-").strip("-").lower()
    params = urllib.parse.urlencode({"keyword": kw_slug, "location": loc_slug})
    return f"{SEARCH_URL}?{params}"


def retry_with_backoff(url: str, max_retries: int = 3) -> requests.Response | None:
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After", "5")
                wait = int(retry_after) if retry_after.isdigit() else min(attempt * 5, 30)
                log.warning("HTTP 429 (attempt %d/%d). Waiting %ds...", attempt, max_retries, wait)
                time.sleep(wait)
                continue

            if resp.status_code == 403:
                log.warning("HTTP 403 (attempt %d/%d). Waiting 10s...", attempt, max_retries)
                time.sleep(10)
                if attempt < max_retries:
                    continue
                return None

            if resp.status_code != 200:
                log.warning("HTTP %d (attempt %d/%d)", resp.status_code, attempt, max_retries)
                return None

            return resp

        except requests.RequestException as e:
            log.warning("Connection error (attempt %d/%d): %s", attempt, max_retries, e)
            if attempt < max_retries:
                time.sleep(min(attempt * 5, 30))

    return None


def parse_offers(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    offers: list[dict] = []
    today = date.today().isoformat()

    cards = soup.select("div.result-item")
    for card in cards:
        try:
            offer = parse_card(card, today)
            if offer:
                offers.append(offer)
        except Exception as e:
            log.debug("Error parsing card: %s", e)

    return offers


def extract_ga4_data(card) -> dict | None:
    bind = card.select_one(".js-area-bind, .area-bind, [data-ga4-offerdata]")
    if not bind:
        return None
    raw = bind.get("data-ga4-offerdata")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def parse_card(card, today: str) -> dict | None:
    ga4 = extract_ga4_data(card)

    link_el = card.select_one("h2.item-title a, h2 a, a.titulo, a.js-offer-title")
    url = ""
    if link_el and link_el.get("href"):
        href = link_el["href"]
        if href.startswith("/"):
            url = f"https://www.elempleo.com{href}"
        else:
            url = href
    elif ga4 and ga4.get("id"):
        url = f"https://www.elempleo.com/co/ofertas-trabajo/{ga4.get('title', 'oferta')}-{ga4['id']}".lower().replace(" ", "-")

    title = ""
    if ga4 and ga4.get("title"):
        title = ga4["title"]
    if not title:
        title_el = card.select_one("a.js-offer-title, a.titulo, h2 a")
        title = title_el.get_text(strip=True) if title_el else ""

    company = ""
    if ga4 and ga4.get("company"):
        company = ga4["company"]
    if not company:
        company_el = card.select_one("span.info-company-name, .company-name-text span + span, .js-offer-company")
        company = company_el.get_text(strip=True) if company_el else ""

    location = ""
    if ga4 and ga4.get("location"):
        location = ga4["location"]

    salary = ""
    if ga4 and ga4.get("salary"):
        salary = ga4["salary"]

    desc_div = card.select_one(
        "div.js-area-bind ~ div, div.area-bind ~ div, "
        "[class*='description'], [class*='descripcion'], "
        ".result-item p, .result-item div:not(.hide)"
    )
    description = ""
    if desc_div:
        text = desc_div.get_text(strip=True)
        if len(text) > 50:
            description = text

    if not title and not url:
        return None

    return {
        "portal": "elempleo",
        "url": url,
        "title": title,
        "company": company,
        "location": location,
        "salary": salary,
        "description": description,
        "skills_mentioned": [],
        "date_posted": today,
        "date_scraped": today,
    }


def scrape(keywords: str, location: str, max_results: int) -> list[dict]:
    url = build_search_url(keywords, location)
    log.info("Fetching: keywords=%s location=%s", keywords, location)

    resp = retry_with_backoff(url)
    if resp is None:
        log.warning("Failed to fetch after retries")
        return []

    offers = parse_offers(resp.text)
    log.info("Found %d offers", len(offers))
    return offers[:max_results]


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
