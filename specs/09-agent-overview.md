# Agent Overview

## Purpose
Autonomous job-search agent built on Pico Claw framework. Scrapes job portals, matches offers against CV, notifies via Telegram.

## Architecture
```
Pico Claw Gateway/CLI
├── Skills (autonomous capabilities)
│   ├── scraper_computrabajo → BeautifulSoup
│   ├── scraper_elempleo    → BeautifulSoup
│   ├── scraper_indeed      → BeautifulSoup
│   ├── scraper_linkedin    → BeautifulSoup + requests
│   ├── matcher             → Semantic CV comparison
│   ├── cv_adapter          → Tailored CV generation
│   └── telegram_bot        → Notification channel
├── Agent Context
│   ├── curriculum.md       → CV in Markdown (source of truth)
│   ├── AGENTS.md           → Agent identity and behavior
│   └── SKILLS.md           → Skill inventory and usage
└── LLM Backend
    └── One API → Groq (primary) + OpenRouter/Gemini (future)
```

## Key Constraints
- CV is the SOURCE OF TRUTH — never fabricate experience
- Match score threshold: > 70% default (configurable)
- Search frequency: every 4 hours (configurable)
- Only notify on NEW offers (deduplication by URL + title)
- All LLM calls routed through One API
- Primary market: Colombia and remote LatAm positions

## Skill Inventory

| Skill | Type | Purpose | Priority | Status |
|-------|------|---------|:--------:|--------|
| scraper_computrabajo | Tool | Scrape Computrabajo Colombia | P1 | Implemented |
| scraper_elempleo | Tool | Scrape elempleo.com | P1 | Implemented |
| scraper_indeed | Tool | Scrape Indeed Colombia | P1 | Implemented |
| scraper_linkedin | Tool | Scrape LinkedIn Colombia | P2 | Implemented |
| matcher | Tool | Semantic CV vs offer comparison | P1 | Implemented |
| cv_adapter | Tool | Generate tailored CV version | P2 | Planned |
| telegram_bot | Channel | Notifications + commands | P1 | Planned |
| devops_qa | Tool | Pre-deploy validation + post-deploy smoke test | P1 | Implemented |

## Requirements
- R-AG-001: Agent MUST use One API as the sole LLM endpoint
- R-AG-002: CV MUST be in Markdown format at `cv/curriculum.md`
- R-AG-003: Match scores MUST be 0-100 based on semantic comparison
- R-AG-004: Default match threshold is 70%, configurable via `config/search_params.yaml`
- R-AG-005: CV adapter MUST NOT fabricate experience — only reorder and highlight
- R-AG-006: Telegram commands MUST be idempotent (no duplicate notifications)
- R-AG-007: Search deduplication MUST use (URL, title) as composite key
- R-AG-008: Each skill MUST have its own spec file in specs/skills/
