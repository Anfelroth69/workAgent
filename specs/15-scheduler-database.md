# Scheduler & Database

## Scheduler

### Configuration
```yaml
schedule:
  automatic: true
  frequency: "cada 4 horas"   # APScheduler cron expression
  notify_only_new: true       # Skip already-seen offers
  timezone: "Europe/Madrid"   # Configurable
```

### Implementation
- APScheduler running inside Pico Claw container
- Each cycle: run all scrapers → run matcher → CV adapter (if needed) → notify
- Idempotent: running the same cycle twice produces the same notifications

## Database

### Storage
SQLite at `/data/seen_offers.db`

### Tables

```sql
CREATE TABLE seen_offers (
  id TEXT PRIMARY KEY,
  url_hash TEXT NOT NULL,
  title_hash TEXT NOT NULL,
  portal TEXT NOT NULL,
  title TEXT NOT NULL,
  company TEXT,
  score INTEGER,
  notified BOOLEAN DEFAULT 0,
  adapted BOOLEAN DEFAULT 0,
  first_seen DATE NOT NULL,
  last_seen DATE NOT NULL
);

CREATE TABLE provider_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  status INTEGER,
  latency_ms INTEGER,
  timestamp DATE NOT NULL
);

CREATE TABLE search_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cycle_id TEXT NOT NULL,
  started_at DATE NOT NULL,
  completed_at DATE,
  offers_found INTEGER,
  matches_found INTEGER,
  errors TEXT
);
```

### Cleanup
- Auto-remove seen_offers older than 30 days
- Auto-remove provider_usage older than 7 days
- Auto-remove search_history older than 90 days

## Requirements
- R-SCH-001: Scheduler MUST be idempotent (same cycle = same results)
- R-SCH-002: Failed cycle MUST NOT block the next scheduled cycle
- R-SCH-003: Database MUST use SQLite (zero dependencies)
- R-SCH-004: Deduplication key MUST be (url_hash, title_hash) composite
- R-SCH-005: Provider usage logging MUST include response time for monitoring
- R-SCH-006: Old records MUST be auto-purged per the cleanup schedule
- R-SCH-007: Database path MUST be configurable via env var
