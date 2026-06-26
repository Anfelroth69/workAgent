#!/usr/bin/env python3
"""HTTP server that runs scraper + matcher for on-demand testing."""

import json
import logging
import os
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("test_runner")

HOST = "127.0.0.1"
PORT = 5002

SKILLS_DIR = "/app/skills"
ROOT_DIR = "/app"


class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/test":
            self.run_test()
        elif parsed.path == "/api/health":
            self.send_json({"status": "ok"})
        else:
            self.send_error(404, descricao="Not found")

    def run_test(self):
        scraper_path = os.path.join(SKILLS_DIR, "scraper_elempleo", "scripts", "scrape.py")
        if not os.path.exists(scraper_path):
            self.send_json({"error": f"Scraper not found at {scraper_path}"}, 500)
            return

        log.info("Running elempleo scraper...")
        try:
            result = subprocess.run(
                [sys.executable, scraper_path, "--keywords", "call center", "--max-results", "5"],
                capture_output=True, text=True, timeout=60,
            )
        except subprocess.TimeoutExpired:
            self.send_json({"error": "Scraper timed out"}, 500)
            return

        if result.returncode != 0:
            self.send_json({
                "error": "Scraper failed",
                "stderr": result.stderr[:1000],
            }, 500)
            return

        offers = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line:
                try:
                    offers.append(json.loads(line))
                except json.JSONDecodeError as e:
                    log.warning("Skipping invalid JSON line: %s", e)

        log.info("Scraped %d offers. Running matcher...", len(offers))
        matcher_path = os.path.join(SKILLS_DIR, "matcher", "scripts", "match.py")
        matched = []

        for offer in offers:
            try:
                m_result = subprocess.run(
                    [sys.executable, matcher_path, "--offer", json.dumps(offer)],
                    capture_output=True, text=True, timeout=60,
                )
                if m_result.returncode == 0 and m_result.stdout.strip():
                    try:
                        match_data = json.loads(m_result.stdout.strip())
                        matched.append({**offer, "match": match_data})
                    except json.JSONDecodeError:
                        matched.append({**offer, "match_error": "Invalid match JSON"})
                else:
                    matched.append({
                        **offer,
                        "match_error": m_result.stderr[:500] or f"exit code {m_result.returncode}",
                    })
            except subprocess.TimeoutExpired:
                matched.append({**offer, "match_error": "Matcher timed out"})
            except Exception as e:
                matched.append({**offer, "match_error": str(e)})

        self.send_json({
            "offers_scraped": len(offers),
            "offers_matched": len(matched),
            "results": matched,
        })

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def log_message(self, fmt, *args):
        log.info(fmt, *args)


def main():
    server = HTTPServer((HOST, PORT), TestHandler)
    log.info("Test runner listening on %s:%d", HOST, PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()


if __name__ == "__main__":
    main()
