---
name: scraper-weremoto
description: >-
  Scrape job listings from weremoto.com. Portal de trabajos remotos enfocado
  en Latinoamérica con categorías de Atención al Cliente, Ventas, Soporte
  Administrativo y más. Uses Playwright for JS-rendered Webflow CMS content.
  Triggers: automated search cycle, /buscar command, user asks for remote jobs.
---

# Scraper WeRemoto

Scrapes weremoto.com and returns normalized offers.
The site uses Webflow CMS; Playwright is needed for full content rendering.

## When to use

- Automated search cycle (every 4 hours via scheduler) — P2 portal
- User requests `/buscar` command on Telegram
- User asks for remote work in LATAM

## How to use

1. Read keywords from `config/search_params.yaml`
2. Run the scraper script:
   ```
   python3 /app/skills/scraper_weremoto/scripts/scrape.py \
     --keywords "call center,atención al cliente" \
     --max-results 25
   ```
3. The script fetches the search page and main page via Playwright
4. Falls back to requests if Playwright is unavailable (limited results)
5. Filters offers client-side by keyword relevance
6. Outputs NDJSON (one JSON object per line)

## Output format (NDJSON)

```json
{
  "portal": "weremoto",
  "url": "https://www.weremoto.com/job-posts/id-asesor-call-center",
  "title": "Asesor Call Center",
  "company": "Empresa SAS",
  "location": "Colombia, Remoto",
  "salary": "",
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

- Empty page: retry with longer wait for JS rendering
- No offers: log and return empty (never error)
- All failures logged to stderr, script exits with code 0

## Rate limiting

Default: 1 request per 2 seconds.
