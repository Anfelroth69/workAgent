---
name: orchestrator
description: >-
  Coordinate the full job-search cycle: scrape portals, deduplicate, match,
  decide, adapt, and notify. Runs automatically on a 4-hour schedule via
  APScheduler.
---

# Orchestrator Skill

Coordinates the 6-step search pipeline: Scrape → Deduplicate → Match → Decide → Adapt → Notify.

## When to use

- On container startup (schedules itself automatically)
- Every 4 hours as the main search cycle
- When a manual full-cycle run is requested

## Pipeline Steps

1. **Scrape** — Execute all P1 scrapers (computrabajo, elempleo, indeed)
2. **Deduplicate** — Skip offers already seen using SQLite database
3. **Match** — Run matcher on each new offer against the CV
4. **Decide** — Score >=70 notify, 50-69 adapt+notify, <50 discard
5. **Adapt** — Run cv_adapter for 50-69% offers
6. **Notify** — Send notification to telegram_bot HTTP endpoint

## How to use

The orchestrator runs automatically. To run the pipeline once without the scheduler:

```bash
python3 skills/orchestrator/scripts/orchestrator.py --once
```

Default (run and schedule every 4 hours):

```bash
python3 skills/orchestrator/scripts/orchestrator.py
```

## Configuration

Read from `config/search_params.yaml`:
- `portals` — list of active portals to scrape
- `keywords` — search keywords
- `match_thresholds` — auto_notify (70%), possible_adapt (50%)
- `weights` — scoring weights for matcher

## Database

SQLite database at `$PICOCLAW_DB_PATH` or `/data/seen_offers.db`.

Tables:
- `seen_offers` — deduplication and notification tracking
- `provider_usage` — scraper latency and status logging
- `search_history` — cycle-level statistics

## Output

Results logged to stdout/stderr. Notifications sent to telegram_bot via HTTP POST to `http://localhost:5003/send-message`.

## Requirements

- R-SCH-001: Idempotent (same cycle = same results)
- R-SCH-002: Failed cycle does not block next cycle
- R-SCH-003: SQLite database (zero external dependencies)
- R-SCH-004: Dedup key = (url_hash, title_hash) composite
- R-SCH-005: Provider usage includes response time
- R-SCH-006: Auto-purge old records per cleanup schedule
- R-SCH-007: Database path configurable via env var

## Parameters

| Env Variable | Purpose |
|---|---|
| `PICOCLAW_API_KEY` | Bearer token for One API (proxied to matcher) |
| `PICOCLAW_DB_PATH` | SQLite database path (default: `/data/seen_offers.db`) |

## Error handling

- Scraper failure: logged, portal skipped, cycle continues
- Matcher failure: logged, offer skipped, cycle continues
- Telegram unavailable: logged, notification lost (idempotent)
- CV adapter failure: logged, notification sent without adapted CV
- APScheduler failure: logged on import
