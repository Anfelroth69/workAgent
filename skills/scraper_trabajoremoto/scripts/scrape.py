#!/usr/bin/env python3
"""
TrabajoRemoto.com Jobs Scraper

Scrapes trabajoremoto.com and outputs NDJSON (one JSON object per line).
Uses Playwright with stealth to bypass Cloudflare protection.
Falls back to requests if Playwright is unavailable.

Usage:
    python3 scrape.py --keywords "call center" --max-results 25
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
log = logging.getLogger("scraper_trabajoremoto")

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

SEARCH_URL = "https://trabajoremoto.com"
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TrabajoRemoto.com Colombia Scraper")
    parser.add_argument("--keywords", default="call center", help="Search keywords")
    parser.add_argument("--location", default="Colombia", help="City or country")
    parser.add_argument("--max-results", type=int, default=25, help="Max offers")
    return parser.parse_args()


def build_search_url(keywords: str) -> str:
    kw = keywords.replace(",", " ").strip()
    params = urllib.parse.urlencode({"s": kw})
    return f"{SEARCH_URL}/?{params}"


def fetch_html(url: str) -> str | None:
    if playwright_fetch:
        log.info("Using Playwright with stealth to bypass WAF")
        html = playwright_fetch(
            url,
            wait_selector="body",
            wait_time=5,
            use_stealth=True,
            mobile=False,
        )
        if html and len(html) > 500:
            return html
        log.warning("Playwright returned too short content (%d bytes)", len(html) if html else 0)

        log.info("Retrying with mobile UA...")
        html = playwright_fetch(
            url,
            wait_selector="body",
            wait_time=5,
            use_stealth=True,
            mobile=True,
        )
        if html and len(html) > 500:
            return html

        log.warning("Playwright blocked by WAF, trying third pass...")
        html = playwright_fetch(
            url,
            wait_selector="body, script",
            wait_time=8,
            use_stealth=True,
            mobile=False,
        )
        if html and len(html) > 500:
            return html

        log.warning("All Playwright attempts blocked by Cloudflare")
        return None

    log.info("Playwright not available, using requests (likely blocked)")
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


def parse_offers(html: str, today: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    offers: list[dict] = []

    cards = soup.select("article, div.oferta, div.job, div.card, div[class*=job], div[class*=offer], div[class*=vacante], li[class*=job]")
    if not cards:
        cards = soup.select("div[class*=resultado], div[class*=listado] > div, main > div, section > div")

    if not cards:
        for tag in ["article", "section", "div"]:
            candidates = soup.find_all(tag, class_=lambda c: c and any(
                x in (c or "").lower() for x in ["job", "offer", "oferta", "vacante", "trabajo", "card", "item", "post"]
            ))
            if candidates:
                cards = candidates
                break

    seen = set()
    for card in cards:
        try:
            offer = parse_card(card, today)
            if offer:
                key = (offer["url"], offer["title"])
                if key not in seen:
                    seen.add(key)
                    offers.append(offer)
        except Exception as e:
            log.debug("Error parsing card: %s", e)

    return offers


def parse_card(card, today: str) -> dict | None:
    link_el = card.select_one("a[href*=trabajoremoto], a[href^=/], a[href^=http]")
    url = ""
    if link_el and link_el.get("href"):
        href = link_el["href"]
        if href.startswith("/"):
            url = f"{SEARCH_URL}{href}"
        elif href.startswith("http"):
            url = href

    title_el = card.select_one(
        "h2 a, h3 a, h4 a, h2, h3, h4, "
        "[class*=title] a, [class*=title], "
        "[class*=titulo] a, [class*=titulo]"
    )
    title = title_el.get_text(strip=True) if title_el else ""

    company_el = card.select_one(
        "[class*=company], [class*=empresa], "
        "[class*=business], [class*=employer]"
    )
    company = company_el.get_text(strip=True) if company_el else ""

    location_el = card.select_one(
        "[class*=location], [class*=ubicacion], "
        "[class*=lugar], [class*=city]"
    )
    location = location_el.get_text(strip=True) if location_el else ""

    salary_el = card.select_one(
        "[class*=salary], [class*=salario], "
        "[class*=price], [class*=sueldo]"
    )
    salary = salary_el.get_text(strip=True) if salary_el else ""

    desc_el = card.select_one(
        "[class*=description], [class*=descripcion], "
        "[class*=summary], [class*=resumen], p"
    )
    description = ""
    if desc_el:
        text = desc_el.get_text(strip=True)
        if len(text) > 30:
            description = text

    if not title and not url:
        return None

    return {
        "portal": "trabajoremoto",
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
    today = date.today().isoformat()
    all_offers: list[dict] = []

    url_patterns = [
        build_search_url(keywords),
        f"{SEARCH_URL}/empleos/",
        f"{SEARCH_URL}/ofertas/",
        f"{SEARCH_URL}/jobs/",
        SEARCH_URL,
    ]

    for url in url_patterns:
        if len(all_offers) >= max_results:
            break
        log.info("Fetching: %s", url)
        html = fetch_html(url)
        if not html:
            log.warning("Failed to fetch %s", url)
            continue
        offers = parse_offers(html, today)
        log.info("Found %d offers at %s", len(offers), url)
        for offer in offers:
            if len(all_offers) >= max_results:
                break
            all_offers.append(offer)

    return all_offers[:max_results]


def main() -> None:
    args = parse_args()
    keywords = args.keywords or os.environ.get("SCRAPER_KEYWORDS", "call center")

    offers = scrape(keywords, args.location, args.max_results)
    for offer in offers:
        print(json.dumps(offer, ensure_ascii=False))

    log.info("Scraped %d offers total from trabajoremoto.com", len(offers))
    sys.exit(0)


if __name__ == "__main__":
    main()
