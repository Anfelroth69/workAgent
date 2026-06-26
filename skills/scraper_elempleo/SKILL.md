---
name: scraper-elempleo
description: >-
  Scrape job listings from elempleo.com Colombia. Portal especializado en
  ofertas de empleo en Colombia con alta presencia de call center, ventas,
  atención al cliente y BPO. Use when the agent needs Colombian job offers.
  Triggers: automated search cycle, /buscar command, user asks for local jobs.
---

# Scraper elempleo Colombia

Scrapes elempleo.com search results and returns normalized offers.

## When to use

- Automated search cycle (every 4 hours via scheduler) — P1 portal
- User requests `/buscar` command on Telegram
- User asks to search for jobs in Colombia
- Primary portal for call center / ventas in Colombia

## How to use

1. Read keywords from `config/search_params.yaml`
   - If `keywords` is empty, extract top skills from `cv/curriculum.md`
2. Run the scraper script:
   ```
   python3 /app/skills/scraper_elempleo/scripts/scrape.py \
     --keywords "call center,ventas por teléfono" \
     --location "Cali" \
     --max-results 25
   ```
3. The script outputs NDJSON (one JSON object per line)
4. Parse each offer and pass to the matcher skill
5. On 429 or 403: retry with exponential backoff (2s, 4s, 8s) up to 3 tries
6. If all retries fail: log the error and continue (never block the cycle)

## Output format (NDJSON)

```json
{
  "portal": "elempleo",
  "url": "https://www.elempleo.com/co/ofertas-empleo/call-center/cali",
  "title": "Asesor Call Center",
  "company": "Empresa Ejemplo SAS",
  "location": "Cali, Valle del Cauca",
  "salary": "$1.500.000",
  "description": "Empresa del sector BPO requiere asesor...",
  "skills_mentioned": ["call center", "servicio al cliente"],
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

- HTTP 429: wait `Retry-After` header (or 5s), retry up to 3x
- HTTP 403: wait 10s, retry once, then skip
- Connection error: retry 2x with 5s backoff
- All failures logged to stderr, script exits with code 0 (never block)

## Rate limiting

Default: 1 request per 2 seconds for elempleo.
