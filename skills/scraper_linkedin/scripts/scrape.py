#!/usr/bin/env python3
"""
LinkedIn Jobs Scraper (Colombia)

Scrapes LinkedIn Jobs search and outputs NDJSON (one JSON object per line).
Usage:
    python3 scrape.py --keywords "call center,ventas" --location "Colombia" --max-results 25

Output format follows specs/10-skill-scrapers.md common format.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.parse
from datetime import date, datetime
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("scraper_linkedin")

REQUESTS_AVAILABLE = False
BS4_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    pass

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    pass


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DEFAULT_RATE_LIMIT = 3.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LinkedIn Jobs Scraper")
    parser.add_argument("--keywords", default="", help="Comma-separated keywords")
    parser.add_argument("--location", default="remoto", help="Location / modality")
    parser.add_argument("--max-results", type=int, default=25, help="Max offers")
    return parser.parse_args()


def build_search_url(keywords: str, location: str, start: int = 0) -> str:
    params: dict[str, Any] = {
        "keywords": keywords,
        "location": location,
        "start": start,
    }
    return f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"


def retry_with_backoff(url: str, headers: dict, max_retries: int = 3) -> requests.Response | None:
    if not REQUESTS_AVAILABLE:
        log.error("requests library not available")
        return None

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=30)

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
                if attempt < max_retries:
                    time.sleep(min(attempt * 5, 30))
                    continue
                return None

            return resp

        except requests.RequestException as e:
            log.warning("Connection error (attempt %d/%d): %s", attempt, max_retries, e)
            if attempt < max_retries:
                time.sleep(min(attempt * 5, 30))

    return None


def parse_linkedin_html(html: str) -> list[dict]:
    if not BS4_AVAILABLE:
        log.error("BeautifulSoup not available, falling back to regex parsing")
        return parse_linkedin_regex(html)

    soup = BeautifulSoup(html, "html.parser")
    offers: list[dict] = []

    job_cards = soup.select("li[data-entity-urn^='urn:li:jobPosting:']")
    if not job_cards:
        job_cards = soup.select("div.base-card, div.job-search-card, li.job-result-card")

    today = date.today().isoformat()

    for card in job_cards:
        try:
            offer = parse_job_card(card, today)
            if offer:
                offers.append(offer)
        except Exception as e:
            log.debug("Error parsing card: %s", e)

    return offers


def parse_job_card(card, today: str) -> dict | None:
    link_el = card.select_one("a.base-card__full-link, a.job-search-card__title")
    url = ""
    if link_el and link_el.get("href"):
        url = link_el["href"].split("?")[0]

    title_el = card.select_one(
        "h3.base-search-card__title, "
        "span.job-result-card__title, "
        "a.job-search-card__title"
    )
    title = title_el.get_text(strip=True) if title_el else ""

    company_el = card.select_one(
        "h4.base-search-card__subtitle, "
        "a.job-search-card__subtitle, "
        "span.job-result-card__company-name"
    )
    company = company_el.get_text(strip=True) if company_el else ""

    location_el = card.select_one(
        "span.job-search-card__location, "
        "span.base-search-card__metadata-item"
    )
    location_text = location_el.get_text(strip=True) if location_el else ""

    metadata_el = card.select_one("time")
    date_posted = today
    if metadata_el and metadata_el.get("datetime"):
        date_posted = metadata_el["datetime"]

    if not title and not url:
        return None

    return {
        "portal": "linkedin",
        "url": url,
        "title": title,
        "company": company,
        "location": location_text,
        "salary": "",
        "description": "",
        "skills_mentioned": [],
        "date_posted": date_posted,
        "date_scraped": today,
    }


def parse_linkedin_regex(html: str) -> list[dict]:
    today = date.today().isoformat()
    offers: list[dict] = []

    patterns = [
        r'data-entity-urn="urn:li:jobPosting:(\d+)"[^>]*>.*?'
        r'base-search-card__title[^>]*>(.*?)</',
        r'job-result-card[^>]*>.*?'
        r'job-result-card__title[^>]*>(.*?)</',
    ]

    for pattern in patterns:
        matches = re.finditer(pattern, html, re.DOTALL)
        for m in matches:
            post_id = m.group(1) if m.lastindex >= 1 else ""
            title = m.group(m.lastindex).strip() if m.lastindex else ""
            if title:
                offers.append({
                    "portal": "linkedin",
                    "url": f"https://www.linkedin.com/jobs/view/{post_id}" if post_id else "",
                    "title": title,
                    "company": "",
                    "location": "",
                    "salary": "",
                    "description": "",
                    "skills_mentioned": [],
                    "date_posted": today,
                    "date_scraped": today,
                })

    return offers


def scrape(keywords: str, location: str, max_results: int) -> list[dict]:
    if not REQUESTS_AVAILABLE:
        log.error("Cannot scrape: 'requests' library not installed")
        return []

    all_offers: list[dict] = []
    start = 0

    while len(all_offers) < max_results:
        url = build_search_url(keywords, location, start)
        log.info("Fetching: keywords=%s location=%s start=%d", keywords, location, start)

        resp = retry_with_backoff(url, HEADERS)
        if resp is None:
            log.warning("Failed to fetch after retries at start=%d", start)
            break

        offers = parse_linkedin_html(resp.text)
        if not offers:
            log.info("No offers found at start=%d, stopping", start)
            break

        all_offers.extend(offers)
        log.info("Found %d offers (total: %d)", len(offers), len(all_offers))
        start += len(offers)

        if len(offers) < 10:
            break

        time.sleep(DEFAULT_RATE_LIMIT)

    return all_offers[:max_results]


def main() -> None:
    args = parse_args()

    keywords = args.keywords or os.environ.get("SCRAPER_KEYWORDS", "")
    location = args.location or os.environ.get("SCRAPER_LOCATION", "remoto")

    offers = scrape(keywords, location, args.max_results)

    for offer in offers:
        print(json.dumps(offer, ensure_ascii=False))

    log.info("Scraped %d offers total", len(offers))
    sys.exit(0)


if __name__ == "__main__":
    main()
