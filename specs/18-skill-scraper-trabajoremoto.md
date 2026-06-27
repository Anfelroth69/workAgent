# Skill: Scraper TrabajoRemoto.com

## Purpose
Scrape job listings from trabajoremoto.com, a Spanish-language remote job portal for Colombia.

## Target Portal

| Attribute | Value |
|-----------|-------|
| Portal | TrabajoRemoto.com |
| Domain | `trabajoremoto.com` |
| Method | Playwright + stealth (primary), requests fallback |
| Priority | P2 |
| Status | Implemented |

## Search URL
- Base: `https://trabajoremoto.com`
- Search: `https://trabajoremoto.com/?s={keywords}`
- Fallback patterns: `/empleos/`, `/ofertas/`, `/jobs/`

## Output Format

Common normalized format (NDJSON) per `specs/10-skill-scrapers.md`.

## Configuration

Configured in `config/search_params.yaml` under `portals`.

## Requirements

- R-TR-001: Must handle 403 (Cloudflare) gracefully with Playwright stealth retry
- R-TR-002: Must use Playwright with stealth patches for WAF bypass
- R-TR-003: Must output the common normalized format
- R-TR-004: Failed scrapes must log the error and continue (never block)
- R-TR-005: Rate limit of 2s between requests
- R-TR-006: Must try multiple URL patterns if primary fails
