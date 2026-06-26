# Skills Inventory — Pico Claw Agent

Each skill has its own subdirectory. Every skill must have:
- `SKILL.md` — Skill definition with YAML frontmatter (name, description) + instructions
- `scripts/` — Implementation scripts (Python, shell, or direct)

| Directory | Spec Reference | Purpose | Method | Priority | Status |
|-----------|---------------|---------|--------|:--------:|--------|
| `scraper_computrabajo/` | `specs/10-skill-scrapers.md` | Computrabajo Colombia | Playwright + BS4 | P1 | Implemented |
| `scraper_elempleo/` | `specs/10-skill-scrapers.md` | elempleo.com | BS4 + requests | P1 | Implemented |
| `scraper_indeed/` | `specs/10-skill-scrapers.md` | Indeed Colombia | Playwright + BS4 | P1 | Implemented |
| `scraper_linkedin/` | `specs/10-skill-scrapers.md` | LinkedIn Colombia | BS4 + requests | P2 | Implemented |
| `matcher/` | `specs/11-skill-matcher.md` | CV vs offer matching | P1 | Implemented |
| `cv_adapter/` | `specs/12-skill-cv-adapter.md` | Tailored CV generation | P2 | Planned |
| `telegram_bot/` | `specs/13-channel-telegram.md` | Telegram notifications | P1 | Planned |
| `devops_qa/` | `specs/16-skill-devops-qa.md` | Pre-deploy validation + smoke testing | P1 | Implemented |

## Constitution Rules that bind skills
- **Rule 9** — Never fabricate experience
- **Rule 10** — CV is source of truth
- **Rule 11** — Skill spec completeness before implementation
