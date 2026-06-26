---
name: scraper-linkedin
description: >-
  Scrape job listings from LinkedIn Colombia (co.linkedin.com). Use when the
  agent needs to find job offers in Colombia or remote LatAm matching given
  keywords, location, and modality criteria. P2 portal — lower priority than
  Computrabajo, elempleo, or Indeed for Colombia. Supports retry with backoff
  on 429/403, outputs normalized JSON format. Triggers: automated search
  cycle, /buscar command, user asks to find jobs.
---

# Scraper LinkedIn Colombia

Scrapes LinkedIn Jobs search results (Colombia focused) and returns normalized offers.

## When to use

- Automated search cycle (every 4 hours via scheduler) — P2 portal
- User requests `/buscar` command on Telegram
- User asks to search for jobs in Colombia
- After P1 portals (Computrabajo, elempleo, Indeed) have been scraped
- Another skill (e.g., matcher) needs fresh job data

## How to use

1. Read keywords from `config/search_params.yaml`
   - If `keywords` is empty, extract top skills from `cv/curriculum.md`
2. Run the scraper script:
   ```
   python3 /app/skills/scraper_linkedin/scripts/scrape.py \
     --keywords "call center,ventas por teléfono" \
     --location "Colombia" \
     --max-results 25
   ```
3. The script outputs NDJSON (one JSON object per line)
4. Parse each offer and pass to the matcher skill
5. On 429 or 403: retry with exponential backoff (2s, 4s, 8s) up to 3 tries
6. If all retries fail: log the error and continue (never block the cycle)

## Output format (NDJSON)

```json
{
  "portal": "linkedin",
  "url": "https://co.linkedin.com/jobs/view/12345",
  "title": "Asesor de Call Center",
  "company": "Empresa Ejemplo SAS",
  "location": "Cali, Valle del Cauca",
  "salary": "",
  "description": "Importante empresa del sector...",
  "skills_mentioned": [],
  "date_posted": "2026-06-25",
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

- HTTP 429: wait `Retry-After` header (or 5s), retry up to 3x
- HTTP 403: wait 10s, retry once, then skip
- Connection error: retry 2x with 5s backoff
- All failures logged to stderr, script exits with code 0 (never block)

## Rate limiting

Respect `config/search_params.yaml` rate limits per portal.
Default: 1 request per 3 seconds for LinkedIn.
