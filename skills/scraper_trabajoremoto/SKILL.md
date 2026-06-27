---
name: scraper-trabajoremoto
description: >-
  Scrape job listings from trabajoremoto.com. Portal especializado en trabajo
  remoto en español con presencia de call center, ventas, atención al cliente
  y BPO en Colombia. Uses Playwright with stealth to bypass Cloudflare WAF.
  Triggers: automated search cycle, /buscar command, user asks for remote jobs.
---

# Scraper TrabajoRemoto Colombia

Scrapes trabajoremoto.com search results and returns normalized offers.
The site uses Cloudflare WAF protection; Playwright with stealth is required.

## When to use

- Automated search cycle (every 4 hours via scheduler) — P2 portal
- User requests `/buscar` command on Telegram
- User asks for remote work opportunities in Colombia

## How to use

1. Read keywords from `config/search_params.yaml`
2. Run the scraper script:
   ```
   python3 /app/skills/scraper_trabajoremoto/scripts/scrape.py \
     --keywords "call center,ventas por teléfono" \
     --max-results 25
   ```
3. The script uses Playwright with stealth (mobile UA fallback) to bypass WAF
4. Falls back to requests if Playwright is unavailable
5. Outputs NDJSON (one JSON object per line)
6. On 403 (Cloudflare): retries with different UA, mobile viewport, stealth patches
7. If all retries fail: log the error and continue (never block the cycle)

## Output format (NDJSON)

```json
{
  "portal": "trabajoremoto",
  "url": "https://trabajoremoto.com/oferta/...",
  "title": "Asesor Call Center",
  "company": "Empresa SAS",
  "location": "Remoto",
  "salary": "",
  "description": "Empresa del sector requiere asesor...",
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

- HTTP 403 (Cloudflare): retry with mobile UA + stealth, 2x
- Playwright error: retry with fresh context up to 2x
- No offers found: log and return empty (never error)
- All failures logged to stderr, script exits with code 0

## Rate limiting

Default: 1 request per 2 seconds.
