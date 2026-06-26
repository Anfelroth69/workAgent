#!/usr/bin/env python3
"""
Computrabajo Colombia Jobs Scraper

Scrapes co.computrabajo.com and outputs NDJSON (one JSON object per line).
Uses Playwright first (bypasses Cloudflare/WAF), falls back to requests.

Usage:
    python3 scrape.py --keywords "call center,ventas" --max-results 25
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
log = logging.getLogger("scraper_computrabajo")

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

try:
    from skills.scraper_utils import playwright_fetch
except ImportError:
    try:
        import sys as _sys
        _sys.path.insert(0, "/app/skills")
        from scraper_utils import playwright_fetch
    except ImportError:
        playwright_fetch = None  # type: ignore

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "Referer": "https://co.computrabajo.com/",
    "DNT": "1",
}

SEARCH_URL = "https://co.computrabajo.com/trabajo-de-{keywords}"
DEFAULT_RATE_LIMIT = 2.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Computrabajo Colombia Scraper")
    parser.add_argument("--keywords", default="call center", help="Search keywords")
    parser.add_argument("--max-results", type=int, default=25, help="Max offers")
    return parser.parse_args()


def build_search_url(keywords: str) -> str:
    slug = keywords.replace(",", "-").replace(" ", "-").strip("-").lower()
    return SEARCH_URL.format(keywords=slug)


def fetch_html(url: str) -> str | None:
    strategies = [
        ("Playwright + stealth + mobile", lambda: playwright_fetch(url, use_stealth=True, mobile=True, wait_time=4) if playwright_fetch else None),
        ("Playwright + stealth", lambda: playwright_fetch(url, use_stealth=True, wait_time=3) if playwright_fetch else None),
        ("Playwright", lambda: playwright_fetch(url, use_stealth=False, wait_time=3) if playwright_fetch else None),
    ]

    for name, fetch_fn in strategies:
        if not playwright_fetch and name != "requests":
            continue
        log.info("Trying: %s", name)
        html = fetch_fn()
        if html and len(html) > 500:
            return html
        time.sleep(2)

    for attempt in range(1, 4):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200 and len(resp.text) > 500:
                return resp.text
            log.warning("Attempt %d/3: status=%d size=%d", attempt, resp.status_code, len(resp.text))
        except requests.RequestException as e:
            log.warning("Attempt %d/3: %s", attempt, e)
        if attempt < 3:
            time.sleep(min(attempt * 5, 15))
    return None


def parse_offers(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    offers: list[dict] = []
    today = date.today().isoformat()

    cards = soup.select("div.box_offer, div.box_offer.outstanding")
    if not cards:
        cards = soup.select("article")
    if not cards:
        cards = soup.select("[class*=oferta], [data-id-oferta], div.box_oferta, li[itemtype]")

    for card in cards:
        try:
            offer = parse_card(card, today)
            if offer:
                offers.append(offer)
        except Exception as e:
            log.debug("Error parsing card: %s", e)

    return offers


def parse_card(card, today: str) -> dict | None:
    link_el = card.select_one("a.js-o-link, a[href*='oferta'], a.tituloOferta, h2 a, h3 a")
    url = ""
    if link_el and link_el.get("href"):
        href = link_el["href"]
        if href.startswith("/"):
            url = f"https://co.computrabajo.com{href}"
        else:
            url = href

    title_el = card.select_one(
        "a.js-o-link, a.fc_base.t_word_wrap, "
        "a[href*='oferta'], a.tituloOferta"
    )
    title = title_el.get_text(strip=True) if title_el else ""

    full_text = card.get_text(separator="|", strip=True)
    parts = full_text.split("|") if full_text else []

    company = ""
    location = ""
    salary = ""
    description = ""

    for text in parts:
        text = text.strip()
        if not text or text == title:
            continue
        if "$" in text and not salary:
            salary = text
        elif any(x in text.lower() for x in ["bogot", "medell", "cali", "antioq", "colombia", "valle", "cundina"]):
            location = text
        elif any(x in text.lower() for x in ["empresa", "s.a", "sas", "ltda", "s.a.s", "bpo", "contact", "concentrix"]):
            company = text
        elif len(text) > 15 and not description:
            description = text

    if not title and not url:
        return None

    return {
        "portal": "computrabajo",
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


def scrape(keywords: str, max_results: int) -> list[dict]:
    url = build_search_url(keywords)
    log.info("Fetching: keywords=%s url=%s", keywords, url)

    html = fetch_html(url)
    if not html:
        log.warning("Failed to fetch after all attempts")
        return []

    offers = parse_offers(html)
    log.info("Found %d offers", len(offers))
    return offers[:max_results]


def main() -> None:
    args = parse_args()
    keywords = args.keywords or os.environ.get("SCRAPER_KEYWORDS", "call center")

    offers = scrape(keywords, args.max_results)
    for offer in offers:
        print(json.dumps(offer, ensure_ascii=False))

    log.info("Scraped %d offers total", len(offers))
    sys.exit(0)


if __name__ == "__main__":
    main()
