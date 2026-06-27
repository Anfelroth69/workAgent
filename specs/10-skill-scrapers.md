# Skill: Scrapers

## Purpose
Scrape job listings from configured portals, normalize into a common format, and pass to the matcher skill.

## Target Portals

| Portal | Method | Domain | Priority |
|--------|--------|--------|:--------:|
| Computrabajo Colombia | Playwright + BS4 | `co.computrabajo.com` | P1 |
| elempleo.com | BS4 + requests | `elempleo.com` | P1 |
| Indeed Colombia | Playwright + BS4 | `co.indeed.com` | P1 |
| LinkedIn Colombia | BS4 + requests | `co.linkedin.com` | P2 |
| TrabajoRemoto.com | Playwright + stealth | `trabajoremoto.com` | P2 |
| WeRemoto | Playwright | `weremoto.com` | P2 |

## Common Output Format

All scrapers MUST output this normalized structure:

```yaml
offer:
  portal: computrabajo      # Source portal ID
  url: https://...          # Direct link to offer
  title: Agente Telefonico  # Job title (normalized)
  company: Acme Corp        # Company name
  location: Cali            # Location / modality
  salary: 1.5M-2M COP       # Salary range (if available)
  description: >            # Full text (cleaned HTML)
    We are looking for...
  skills_mentioned:         # Extracted by agent
    - Call center
    - Ventas
  date_posted: 2026-06-25   # ISO date
  date_scraped: 2026-06-25  # ISO date
```

## Configuration

Configurable in `config/search_params.yaml`:
```yaml
search_params:
  keywords:
    - "call center"
    - "ventas por teléfono"
    - "agente telefónico"
  location: "Colombia"
  modality: ["remote", "presencial", "hibrido"]
  experience_level: ["junior", "mid", "senior"]
  date_posted: "ultimas 24h"
  portals:
    - computrabajo
    - elempleo
    - indeed
    - linkedin
```

Keywords are extracted from CV automatically if empty.

## Portal-specific details

### Computrabajo Colombia
- Domain: `co.computrabajo.com`
- Search URL: `https://co.computrabajo.com/trabajo-de-[keywords]`
- Method: Playwright (headless Chromium) for WAF bypass, fallback to BS4 + requests
- Parsing: BS4 on rendered HTML, select `article` cards
- Rate limit: 2s between requests
- Note: Aggressive WAF may block even Playwright; consider stealth/proxy rotation if consistently 403

### elempleo.com
- Domain: `elempleo.com`
- Search URL: `https://www.elempleo.com/co/ofertas-empleo/?keyword=[keywords]`
- Method: BS4 + requests, parse `div.result-item` cards
- Data source: `data-ga4-offerdata` JSON attribute for reliable location/salary extraction
- Rate limit: 2s between requests
- Note: Server-side keyword search returns all recent offers; filtering is done by the matcher

### Indeed Colombia
- Domain: `co.indeed.com`
- Search URL: `https://co.indeed.com/ofertas?q=[keywords]&l=[location]`
- Method: Playwright (headless Chromium) to bypass Cloudflare, BS4 for parsing
- Parsing: BS4 on rendered HTML, select `div.job_seen_beacon` cards
- Rate limit: 3s between requests

### LinkedIn Colombia
- Domain: `co.linkedin.com`
- Search URL: `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search`
- Method: BS4, parse job card elements
- Rate limit: 3s between requests
- Note: LinkedIn uses the same API endpoint regardless of country; `location` parameter controls region

### TrabajoRemoto.com
- Domain: `trabajoremoto.com`
- Search URL: `https://trabajoremoto.com/?s=[keywords]`
- Method: Playwright + stealth for Cloudflare WAF bypass; falls back to requests
- Parsing: BS4 on rendered HTML, flexible card selectors (article, .job, .card, etc.)
- Rate limit: 2s between requests
- Note: Site behind Cloudflare; Playwright with stealth (mobile UA fallback) required

### WeRemoto
- Domain: `weremoto.com`
- Search URL: `https://www.weremoto.com/search?query=[keywords]`
- Method: Playwright for JS-rendered Webflow CMS content; falls back to requests
- Parsing: BS4 on rendered HTML, select `div.job-item-accordion.w-dyn-item` cards
- Rate limit: 2s between requests
- Note: Webflow CMS site; full job list loaded via client-side JS

## Requirements
- R-SCR-001: Each scraper MUST handle 429/403 gracefully (retry with backoff)
- R-SCR-002: Scrapers MUST use Playwright for WAF/Cloudflare-protected portals (Computrabajo, Indeed, TrabajoRemoto) and JS-rendered portals (WeRemoto); BS4 + requests is sufficient for static portals (elempleo, LinkedIn)
- R-SCR-003: All scrapers MUST output the common normalized format
- R-SCR-004: Failed scrapes MUST log the error and continue (never block)
- R-SCR-005: Deduplication by URL MUST happen at the matcher level
- R-SCR-006: Rate limits per portal MUST be configurable per-portal
- R-SCR-007: Scrapers MUST respect robots.txt when possible
- R-SCR-008: Priority P1 portals MUST be scraped every cycle; P2-P3 are optional
