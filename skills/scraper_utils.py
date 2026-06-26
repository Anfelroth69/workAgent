#!/usr/bin/env python3
"""
Shared utilities for Pico Claw scrapers.
Provides Playwright browser management with retry logic and stealth support.
"""

import logging
import os
import shutil
import time

log = logging.getLogger("scraper_utils")

PLAYWRIGHT_AVAILABLE = False
STEALTH_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

try:
    from playwright_stealth import Stealth
    STEALTH_AVAILABLE = True
except ImportError:
    pass


def get_chromium_path() -> str | None:
    for binary in ["chromium", "chromium-browser", "google-chrome", "google-chrome-stable"]:
        path = shutil.which(binary)
        if path:
            return path
    return None


def playwright_fetch(
    url: str,
    wait_selector: str | None = None,
    wait_time: int = 3,
    timeout: int = 20000,
    max_retries: int = 2,
    use_stealth: bool = True,
    mobile: bool = False,
) -> str | None:
    """Fetch a page using Playwright, return rendered HTML.

    For aggressive WAF sites (Computrabajo), `use_stealth=True` patches
    headless detection vectors. `mobile=True` uses mobile UA + viewport.

    Args:
        url: Full URL to fetch
        wait_selector: CSS selector to wait for
        wait_time: Seconds to wait after page load
        timeout: Page load timeout in ms
        max_retries: Number of retries on failure
        use_stealth: Apply Playwright stealth patches
        mobile: Use mobile User-Agent and viewport

    Returns:
        Rendered HTML string, or None if failed
    """
    if not PLAYWRIGHT_AVAILABLE:
        log.error("playwright package not installed")
        return None

    stealth = Stealth() if STEALTH_AVAILABLE and use_stealth else None

    for attempt in range(1, max_retries + 1):
        browser = None
        try:
            p = sync_playwright().start()
            chromium_path = get_chromium_path()
            launch_kwargs = {"headless": True}
            if chromium_path:
                launch_kwargs["executable_path"] = chromium_path

            if mobile:
                ua = (
                    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
                )
                viewport = {"width": 412, "height": 915}
            else:
                ua = (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                )
                viewport = {"width": 1920, "height": 1080}

            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(
                user_agent=ua,
                locale="es-CO",
                viewport=viewport,
            )
            page = context.new_page()

            if stealth:
                stealth.apply_stealth_sync(page)

            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            time.sleep(wait_time)

            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=5000)
                except Exception:
                    log.debug("Selector '%s' not found, continuing", wait_selector)

            html = page.content()
            if len(html) > 500:
                return html

            log.warning("Response too short (%d bytes), might be blocked", len(html))

        except Exception as e:
            log.warning("Playwright attempt %d/%d failed: %s", attempt, max_retries, e)
            if attempt < max_retries:
                time.sleep(min(attempt * 5, 15))

        finally:
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass

    return None

