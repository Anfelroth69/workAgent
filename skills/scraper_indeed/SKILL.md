---
name: scraper-indeed
description: >-
  Scrape job listings from Indeed Colombia (co.indeed.com). High-volume portal
  for call center, ventas, atencion al cliente, and BPO positions in Colombia.
  Uses Playwright to bypass Cloudflare protection. Falls back to requests
  if Playwright unavailable. Triggers: automated search cycle, /buscar
  command, user asks for local jobs.
---

# Scraper Indeed Colombia

Scrapes Indeed Colombia search results using Playwright and returns normalized offers.

## When to use

- Automated search cycle (every 4 hours via scheduler) — P1 portal
- User requests `/buscar` command on Telegram
- User asks to search for jobs in Colombia
- High volume of call center / ventas offers

## How to use

1. Read keywords from `config/search_params.yaml`
   - If `keywords` is empty, extract top skills from `cv/curriculum.md`
2. Run the scraper script:
   ```
   python3 /app/skills/scraper_indeed/scripts/scrape.py \
     --keywords "call center,ventas por teléfono" \
     --location "Cali" \
     --max-results 25
   ```
3. The script launches headless Chromium (via Playwright), waits for job cards,
   then outputs NDJSON. Falls back to requests if Playwright is unavailable.
4. Parse each offer and pass to the matcher skill
5. If blocked: retries with a fresh browser context up to 2 times
6. If all retries fail: log the error and continue (never block the cycle)

## Technical note

Indeed uses Cloudflare anti-bot protection. The script uses Playwright with
headless Chromium to render the page fully. Chromium is bundled in the
container (installed via Alpine `chromium` package). The `scraper_utils.py`
module provides shared Playwright browser management.

## Output format (NDJSON)

```json
{
  "portal": "indeed",
  "url": "https://co.indeed.com/ver-oferta?jk=abc123",
  "title": "Asesor de Servicio al Cliente",
  "company": "Empresa Ejemplo SAS",
  "location": "Cali, Valle del Cauca",
  "salary": "$1.300.000 - $1.800.000",
  "description": "Empresa del sector BPO requiere asesor...",
  "skills_mentioned": [],
  "date_posted": "2026-06-24",
  "date_scraped": "2026-06-25"
}
```

## Parameters

| Argument | Default | Description |
|----------|---------|-------------|
| `--keywords` | (from config) | Comma-separated search terms |
| `--location` | "Colombia" | City or country |
| `--max-results` | 25 | Max offers to return |

## Error handling

- Playwright error: retry with fresh browser context up to 2x
- Cloudflare block: fall back to requests (may still be blocked)
- Connection error: retry 2x with 5s backoff
- All failures logged to stderr, script exits with code 0 (never block)

## Rate limiting

Default: 1 request per 3 seconds for Indeed.
