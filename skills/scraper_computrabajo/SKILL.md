---
name: scraper-computrabajo
description: >-
  Scrape job listings from Computrabajo Colombia (co.computrabajo.com).
  Portal #1 for call center, ventas, and BPO in Colombia. Uses Playwright
  to bypass WAF. Falls back to requests if Playwright unavailable.
  Triggers: automated search cycle, /buscar command, user asks for local jobs.
---

# Scraper Computrabajo Colombia

Scrapes Computrabajo Colombia search results and returns normalized offers.

## When to use

- Automated search cycle (every 4 hours via scheduler) — P1 portal
- User requests `/buscar` command on Telegram
- User asks to search for jobs in Colombia

## How to use

1. Read keywords from `config/search_params.yaml`
   - If `keywords` is empty, extract top skills from `cv/curriculum.md`
2. Run the scraper script:
   ```
   python3 /app/skills/scraper_computrabajo/scripts/scrape.py \
     --keywords "call center,ventas por teléfono" \
     --max-results 25
   ```
3. The script tries Playwright first (headless Chromium), falls back to requests
4. Outputs NDJSON (one JSON object per line)
5. Parse each offer and pass to the matcher skill
6. If blocked: retry with fresh browser context up to 2 times
7. If all retries fail: log the error and continue (never block the cycle)

## Technical note

Computrabajo uses aggressive WAF protection. The script uses a multi-strategy
approach:
1. **Playwright + stealth + mobile UA** — best chance of bypass
2. **Playwright + stealth** — desktop UA with headless detection patches
3. **Playwright** — plain headless Chromium
4. **Requests** — fallback (usually blocked)

The `playwright-stealth` package patches common headless detection vectors
(navigator.webdriver, Chrome runtime flags, etc.). Even with all strategies,
Computrabajo may still block due to IP-based rate limiting. This is a known
limitation; consider proxy rotation for production use.

## Output format (NDJSON)

```json
{
  "portal": "computrabajo",
  "url": "https://co.computrabajo.com/oferta-de-trabajo/de/call-center-en-cali",
  "title": "Agente de Call Center",
  "company": "Empresa Ejemplo SAS",
  "location": "Cali, Valle del Cauca",
  "salary": "$1.300.000 - $2.000.000",
  "description": "Importante empresa del sector...",
  "skills_mentioned": [],
  "date_posted": "2026-06-24",
  "date_scraped": "2026-06-25"
}
```

## Parameters

| Argument | Default | Description |
|----------|---------|-------------|
| `--keywords` | (from config) | Comma-separated search terms |
| `--max-results` | 25 | Max offers to return |

## Error handling

- Playwright error: retry with fresh browser context up to 2x
- WAF block: fall back to requests with 10s delay
- Connection error: retry 2x with 5s backoff
- All failures logged to stderr, script exits with code 0 (never block)

## Rate limiting

Default: 1 request per 2 seconds for Computrabajo.
