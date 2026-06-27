#!/usr/bin/env python3
"""
WeRemoto.com Jobs Scraper

Scrapes weremoto.com (Webflow CMS site) and outputs NDJSON.
Uses Playwright to handle JS-rendered job listings.
Falls back to requests if Playwright is unavailable.

Usage:
    python3 scrape.py --keywords "call center" --max-results 25
"""

import argparse
import json
import logging
import os
import re
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
log = logging.getLogger("scraper_weremoto")

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
        playwright_fetch = None

BASE_URL = "https://www.weremoto.com"
SEARCH_URL = "https://www.weremoto.com/search"
DEFAULT_RATE_LIMIT = 2.0
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "DNT": "1",
}


MONTHS_ES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WeRemoto.com Scraper")
    parser.add_argument("--keywords", default="call center", help="Search keywords")
    parser.add_argument("--location", default="Colombia", help="City or country")
    parser.add_argument("--max-results", type=int, default=25, help="Max offers")
    return parser.parse_args()


def build_search_url(keywords: str) -> str:
    kw = keywords.replace(",", " ").strip()
    params = urllib.parse.urlencode({"query": kw})
    return f"{SEARCH_URL}?{params}"


def fetch_page_html(url: str) -> str | None:
    if playwright_fetch:
        log.info("Using Playwright for JS-rendered content")
        html = playwright_fetch(
            url,
            wait_selector="div.job-item-accordion, div.w-dyn-item",
            wait_time=5,
        )
        if html and len(html) > 500:
            return html
        log.warning("Playwright returned short content (%d bytes)", len(html) if html else 0)
        html = playwright_fetch(
            url,
            wait_selector="body",
            wait_time=8,
        )
        if html and len(html) > 500:
            return html
        log.warning("Playwright failed to get content")
        return None

    log.info("Playwright not available, using requests (jobs may not load)")
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


def parse_date(date_text: str, today: str) -> str:
    date_text = date_text.strip()
    if not date_text:
        return today

    if date_text.lower() == "hoy":
        return today
    if date_text.lower() in ("ayer", "ayer"):
        from datetime import timedelta, datetime as dt
        return (dt.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    m = re.match(r"(\d{1,2})\s+(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)", date_text.lower())
    if m:
        day = int(m.group(1))
        month = MONTHS_ES.get(m.group(2), 1)
        year = date.today().year
        return f"{year:04d}-{month:02d}-{day:02d}"

    return today


def parse_offers(html: str, keywords: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    offers: list[dict] = []
    today = date.today().isoformat()

    cards = soup.select("div.job-item-accordion.w-dyn-item")
    if not cards:
        cards = soup.select("[role=listitem].w-dyn-item, div.w-dyn-item")

    seen = set()
    kw_lower = keywords.lower()

    for card in cards:
        try:
            offer = parse_card(card, today)
            if offer:
                text_for_filter = f"{offer['title']} {offer['company']} {offer['description']}".lower()
                if kw_lower and not any(kw.strip().lower() in text_for_filter for kw in keywords.split(",")):
                    continue
                key = (offer["url"], offer["title"])
                if key not in seen:
                    seen.add(key)
                    offers.append(offer)
        except Exception as e:
            log.debug("Error parsing card: %s", e)

    return offers


def parse_card(card, today: str) -> dict | None:
    title_el = card.select_one("h4.job-title, [fs-cmsfilter-field=title], h4")
    title = title_el.get_text(strip=True) if title_el else ""

    company_el = card.select_one("div.company-name, [fs-cmsfilter-field=company]")
    company = company_el.get_text(strip=True) if company_el else ""

    location = ""
    location_els = card.select("div.remoto")
    if location_els:
        loc_text = location_els[0].get_text(strip=True)
        loc_text = re.sub(r"[📍🌎]", "", loc_text).strip()
        if loc_text and loc_text not in ("Remoto",):
            location = loc_text

    salary = ""

    desc_el = card.select_one("div.job-detail-details.w-richtext")
    description = ""
    if desc_el:
        text = desc_el.get_text(strip=True)
        if len(text) > 30:
            description = text

    date_text = today
    date_el = card.select_one("div.date._2, div.date")
    if date_el:
        date_text = parse_date(date_el.get_text(strip=True), today)

    url = ""
    link_el = card.select_one("a.job-button-view, a.apply-button")
    if link_el and link_el.get("href"):
        href = link_el["href"]
        if href.startswith("/"):
            url = f"{BASE_URL}{href}"
        else:
            url = href

    if not title and not url:
        return None

    return {
        "portal": "weremoto",
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

    primary_url = build_search_url(keywords)
    log.info("Fetching: %s", primary_url)
    html = fetch_page_html(primary_url)
    if html:
        offers = parse_offers(html, keywords)
        log.info("Found %d offers from search", len(offers))
        all_offers.extend(offers)

    if len(all_offers) < max_results:
        time.sleep(DEFAULT_RATE_LIMIT)
        log.info("Fetching main page for additional offers: %s", BASE_URL)
        html = fetch_page_html(BASE_URL)
        if html:
            offers = parse_offers(html, keywords)
            log.info("Found %d offers from main page", len(offers))
            existing_urls = {o["url"] for o in all_offers}
            for offer in offers:
                if offer["url"] not in existing_urls and len(all_offers) < max_results:
                    all_offers.append(offer)

    return all_offers[:max_results]


def main() -> None:
    args = parse_args()
    keywords = args.keywords or os.environ.get("SCRAPER_KEYWORDS", "call center")

    offers = scrape(keywords, args.location, args.max_results)
    for offer in offers:
        print(json.dumps(offer, ensure_ascii=False))

    log.info("Scraped %d offers total from weremoto.com", len(offers))
    sys.exit(0)


if __name__ == "__main__":
    main()
