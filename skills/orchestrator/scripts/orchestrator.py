#!/usr/bin/env python3
"""
Pico Claw Orchestrator.

Coordinates the 6-step job-search pipeline: Scrape -> Deduplicate -> Match
-> Decide -> Adapt -> Notify. Runs on a 4-hour schedule via APScheduler.

Usage:
    python3 orchestrator.py          # Run immediately + start scheduler
    python3 orchestrator.py --once   # Run once and exit
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("orchestrator")

try:
    import yaml
except ImportError:
    log.error("PyYAML is required: pip install pyyaml")
    sys.exit(1)

import dedup

TELEGRAM_BOT_URL = "http://localhost:5003/send-message"

SKILL_DIR_MAP = {
    "computrabajo": "scraper_computrabajo",
    "elempleo": "scraper_elempleo",
    "indeed": "scraper_indeed",
    "linkedin": "scraper_linkedin",
    "trabajoremoto": "scraper_trabajoremoto",
    "weremoto": "scraper_weremoto",
}


def _project_root() -> str:
    dir_ = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(dir_, "cv")) and os.path.isfile(
            os.path.join(dir_, "cv", "curriculum.md")
        ):
            return dir_
        parent = os.path.dirname(dir_)
        if parent == dir_:
            break
        dir_ = parent
    return "/app"


def load_config(root: str) -> dict:
    path = os.path.join(root, "config", "search_params.yaml")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def run_scraper(
    portal: str, root: str, keywords: list, max_results: int = 10
) -> list:
    skill_dir = SKILL_DIR_MAP.get(portal)
    if not skill_dir:
        log.warning("Unknown portal: %s, skipping", portal)
        return []

    scraper_path = os.path.join(root, "skills", skill_dir, "scripts", "scrape.py")
    if not os.path.exists(scraper_path):
        log.warning("Scraper not found at %s, skipping", scraper_path)
        return []

    kw_str = ", ".join(keywords)
    start = time.time()
    log.info("Running %s scraper...", portal)

    try:
        result = subprocess.run(
            [
                sys.executable,
                scraper_path,
                "--keywords",
                kw_str,
                "--max-results",
                str(max_results),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        latency_ms = int((time.time() - start) * 1000)
        dedup.log_provider_usage(portal, scraper_path, result.returncode, latency_ms)

        if result.returncode != 0:
            log.error(
                "%s scraper failed (exit %d): %s",
                portal,
                result.returncode,
                result.stderr[:500],
            )
            return []

        offers = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line:
                try:
                    offers.append(json.loads(line))
                except json.JSONDecodeError as e:
                    log.warning("Invalid JSON from %s: %s", portal, e)

        log.info("%s returned %d offers", portal, len(offers))
        return offers

    except subprocess.TimeoutExpired:
        log.error("%s scraper timed out after 120s", portal)
        dedup.log_provider_usage(portal, scraper_path, -1, 120000)
        return []
    except Exception as e:
        log.error("%s scraper error: %s", portal, e)
        return []


def run_matcher(offer: dict, root: str) -> dict:
    matcher_path = os.path.join(
        root, "skills", "matcher", "scripts", "match.py"
    )
    if not os.path.exists(matcher_path):
        log.error("Matcher not found at %s", matcher_path)
        return {"score": 0, "error": "matcher_not_found"}

    try:
        result = subprocess.run(
            [sys.executable, matcher_path, "--offer", json.dumps(offer)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            log.error(
                "Matcher failed for %s: %s",
                offer.get("title", "unknown"),
                result.stderr[:300],
            )
            return {"score": 0, "error": result.stderr[:300]}
        if not result.stdout.strip():
            log.error("Matcher empty output for %s", offer.get("title", "unknown"))
            return {"score": 0, "error": "empty_output"}
        return json.loads(result.stdout.strip())
    except subprocess.TimeoutExpired:
        log.error("Matcher timed out for %s", offer.get("title", "unknown"))
        return {"score": 0, "error": "timeout"}
    except json.JSONDecodeError:
        log.error("Invalid match JSON for %s", offer.get("title", "unknown"))
        return {"score": 0, "error": "invalid_json"}
    except Exception as e:
        log.error("Matcher error for %s: %s", offer.get("title", "unknown"), e)
        return {"score": 0, "error": str(e)}


def run_adapter(offer: dict, match: dict, root: str) -> dict:
    adapter_path = os.path.join(
        root, "skills", "cv_adapter", "scripts", "adapt.py"
    )
    if not os.path.exists(adapter_path):
        log.warning("CV adapter not found at %s, skipping", adapter_path)
        return {}

    try:
        result = subprocess.run(
            [
                sys.executable,
                adapter_path,
                "--offer",
                json.dumps(offer),
                "--match",
                json.dumps(match),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            log.error("CV adapter failed: %s", result.stderr[:300])
            return {}
        if result.stdout.strip():
            return json.loads(result.stdout.strip())
        return {}
    except Exception as e:
        log.error("CV adapter error: %s", e)
        return {}


def notify_telegram(text: str, chat_id: str = "") -> bool:
    if not chat_id:
        chat_id = os.environ.get("TELEGRAM_OWNER_ID", "")
    if not chat_id:
        log.warning("TELEGRAM_OWNER_ID not set, cannot notify")
        return False
    payload = {"chat_id": chat_id, "text": text}
    req = urllib.request.Request(
        TELEGRAM_BOT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        log.info("Notification sent to Telegram")
        return True
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        log.error("Failed to notify telegram_bot: %s", e)
        return False
    except Exception as e:
        log.error("Telegram notification error: %s", e)
        return False


def build_notification(offer: dict, match: dict, adapted_path: str = "") -> str:
    score = match.get("score", 0)
    title = offer.get("title", "Sin título")
    company = offer.get("company", "Desconocida")
    location = offer.get("location", "Colombia")
    salary = offer.get("salary", "")
    portal = offer.get("portal", "")
    url = offer.get("url", "")
    date_posted = offer.get("date_posted", "")
    skills = match.get("skills_matched", [])
    missing = match.get("skills_missing", [])
    skills_text = ", ".join(skills[:5]) if skills else "N/A"
    missing_text = ", ".join(missing[:5]) if missing else "N/A"

    score_icon = "🎯"
    lines = [
        f"{score_icon} MATCH: {score}%",
        "━" * 25,
        f"💼 {title}",
        f"🏢 {company}",
        f"📍 {location}",
    ]
    if salary:
        lines.append(f"💰 {salary}")
    lines.append(f"🌐 {portal}")
    if date_posted:
        lines.append(f"⏰ {date_posted}")
    lines.append("")
    lines.append(f"📌 Skills: {skills_text}")
    lines.append(f"⚠️ Faltantes: {missing_text}")
    lines.append("")
    if url:
        lines.append(f"🔗 {url}")
    if adapted_path:
        lines.append(f"📄 CV adaptado: {adapted_path}")
    return "\n".join(lines)


def run_pipeline(root: str = None) -> None:
    if root is None:
        root = _project_root()

    try:
        config = load_config(root)
    except Exception as e:
        log.error("Failed to load config: %s", e)
        return

    thresholds = config.get("match_thresholds", {})
    auto_notify = thresholds.get("auto_notify", 70)
    possible_adapt = thresholds.get("possible_adapt", 50)
    portals = config.get("portals", ["computrabajo", "elempleo", "indeed"])
    keywords = config.get("keywords", ["call center"])
    max_results = config.get("max_results_per_scraper", 10)

    cycle_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    log.info("=== Cycle %s started ===", cycle_id)
    dedup.start_cycle(cycle_id)

    errors = []
    total_offers = 0
    total_matches = 0

    try:
        cleaned = dedup.cleanup()
        log.info("Cleaned %d old records", cleaned)
    except Exception as e:
        log.warning("Cleanup failed: %s", e)

    all_new_offers = []
    for portal in portals:
        try:
            offers = run_scraper(portal, root, keywords, max_results)
            for offer in offers:
                url = offer.get("url", offer.get("link", ""))
                title = offer.get("title", "")
                if not url or not title:
                    log.warning("Skipping offer missing url/title from %s", portal)
                    continue
                if dedup.is_seen(url, title):
                    log.debug("Already seen, skipping: %s", title)
                    continue
                all_new_offers.append((portal, offer))
                total_offers += 1
        except Exception as e:
            msg = f"{portal} scraper error: {e}"
            log.error(msg)
            errors.append(msg)

    log.info("New offers: %d", len(all_new_offers))

    for portal, offer in all_new_offers:
        try:
            match = run_matcher(offer, root)
            score = match.get("score", 0)
            url = offer.get("url", offer.get("link", ""))
            title = offer.get("title", "")
            company = offer.get("company", offer.get("empresa", ""))
            offer_id = f"{url}|{title}"

            dedup.mark_seen(
                url=url,
                title=title,
                portal=portal,
                title_text=title,
                company=company,
                score=score,
            )

            if score >= auto_notify:
                total_matches += 1
                text = build_notification(offer, match)
                if notify_telegram(text):
                    dedup.mark_notified(offer_id)
                log.info("Notified: %s (score %d)", title, score)

            elif score >= possible_adapt:
                total_matches += 1
                adapted = run_adapter(offer, match, root)
                adapted_path = adapted.get("adapted_cv", "")
                text = build_notification(offer, match, adapted_path)
                if notify_telegram(text):
                    dedup.mark_notified(offer_id)
                    if adapted_path:
                        dedup.mark_adapted(offer_id)
                log.info("Adapted + notified: %s (score %d)", title, score)

            else:
                log.info("Discarded: %s (score %d)", title, score)

        except Exception as e:
            msg = (
                f"Failed processing '{offer.get('title', '')}' "
                f"from {portal}: {e}"
            )
            log.error(msg)
            errors.append(msg)

    errors_text = "; ".join(errors) if errors else ""
    dedup.complete_cycle(cycle_id, total_offers, total_matches, errors_text)
    log.info(
        "=== Cycle %s completed: %d offers, %d matches ===",
        cycle_id,
        total_offers,
        total_matches,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Pico Claw Orchestrator")
    parser.add_argument(
        "--once", action="store_true", help="Run pipeline once and exit"
    )
    args = parser.parse_args()

    root = _project_root()
    log.info("Project root: %s", root)

    run_pipeline(root)

    if args.once:
        log.info("One-shot run complete.")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        log.error("APScheduler is required for scheduling: pip install apscheduler")
        sys.exit(1)

    scheduler = BackgroundScheduler()
    scheduler.add_job(run_pipeline, "interval", hours=4, args=[root])
    scheduler.start()
    log.info("Scheduler started. Next run in 4 hours.")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        log.info("Shutting down scheduler...")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
