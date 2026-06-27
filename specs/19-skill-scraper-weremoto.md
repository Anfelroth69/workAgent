# Skill: Scraper WeRemoto.com

## Purpose
Scrape job listings from weremoto.com, a Spanish-language remote job portal focused on Latin America.

## Target Portal

| Attribute | Value |
|-----------|-------|
| Portal | WeRemoto |
| Domain | `weremoto.com` |
| Method | Playwright (primary), requests fallback |
| Priority | P2 |
| Status | Implemented |

## Search URL
- Main: `https://www.weremoto.com`
- Search: `https://www.weremoto.com/search?query={keywords}`

## Output Format

Common normalized format (NDJSON) per `specs/10-skill-scrapers.md`.

## Parsing Details

- Job cards: `div.job-item-accordion.w-dyn-item`
- Title: `h4.job-title` or `[fs-cmsfilter-field=title]`
- Company: `div.company-name` or `[fs-cmsfilter-field=company]`
- Location: first `div.remoto` element
- Date: `div.date._2` element
- Description: `div.job-detail-details.w-richtext`

## Configuration

Configured in `config/search_params.yaml` under `portals`.

## Requirements

- R-WR-001: Must use Playwright for JS-rendered Webflow CMS content
- R-WR-002: Must output the common normalized format
- R-WR-003: Failed scrapes must log the error and continue (never block)
- R-WR-004: Rate limit of 2s between requests
- R-WR-005: Must filter offers by keyword relevance client-side
