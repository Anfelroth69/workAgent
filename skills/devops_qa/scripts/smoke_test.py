#!/usr/bin/env python3
"""
Post-deploy smoke test. Run after a Render deploy to verify the service is healthy.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request


def report(status, check, detail=""):
    prefix = {"pass": "[PASS]", "fail": "[FAIL]"}.get(status, "[INFO]")
    msg = f"{prefix} {check}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return status == "pass"


def fetch_json(url, timeout=30):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8")), resp.status


def main():
    parser = argparse.ArgumentParser(description="Smoke test Pico Claw service")
    parser.add_argument("--url", default="http://localhost:3000",
                       help="Base URL of the service (default: http://localhost:3000)")
    args = parser.parse_args()
    base_url = args.url.rstrip("/")

    print("=" * 60)
    print(f"  Pico Claw — Post-deploy Smoke Test")
    print(f"  Target: {base_url}")
    print("=" * 60)
    print()

    passed = 0
    failed = 0

    # Health check
    try:
        data, status = fetch_json(f"{base_url}/api/status")
        if status == 200:
            report("pass", "Health endpoint", f"status={status}")
            passed += 1
        else:
            report("fail", "Health endpoint", f"expected 200, got {status}")
            failed += 1
    except Exception as e:
        report("fail", "Health endpoint", str(e))
        failed += 1

    # One API reachable (endpoint requires auth, 401 means it's alive)
    try:
        data, status = fetch_json(f"{base_url}/v1/models")
        if status == 200:
            models = data.get("data", [])
            if models:
                model_names = [m.get("id", "?") for m in models[:5]]
                report("pass", "One API models",
                       f"{len(models)} models: {', '.join(model_names)}")
            else:
                report("pass", "One API models", "endpoint reachable, no models")
            passed += 1
        elif status == 401:
            report("pass", "One API models", "endpoint reachable (auth required)")
            passed += 1
        else:
            report("fail", "One API models", f"unexpected status {status}")
            failed += 1
    except Exception as e:
        report("fail", "One API models", str(e))
        failed += 1

    # Root responds
    try:
        req = urllib.request.Request(f"{base_url}/")
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status in (200, 302, 301):
                report("pass", "Root endpoint", f"status={resp.status}")
                passed += 1
            else:
                report("fail", "Root endpoint", f"unexpected status {resp.status}")
                failed += 1
    except Exception as e:
        report("fail", "Root endpoint", str(e))
        failed += 1

    print()
    print("=" * 60)
    print(f"  Result: {passed} passed, {failed} failed")
    print("=" * 60)

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
