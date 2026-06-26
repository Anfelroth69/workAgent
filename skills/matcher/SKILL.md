---
name: matcher
description: >-
  Compare scraped job offers against the CV (curriculum.md) using One API LLM
  and compute a semantic match score. Runs after scraping, before notification.
  Triggers: automated search cycle, after scraper skills complete.
---

# Matcher Skill

Compares job offers against the CV using One API (LLM) and computes match scores.

## When to use

- After any scraper skill completes (mandatory step in the search cycle)
- Before sending notifications or triggering CV adaptation
- When the agent needs to decide whether an offer is worth pursuing

## How to use

1. Read thresholds and weights from `config/search_params.yaml`
2. Pipe a job offer (JSON) to the match script:
   ```
   echo '{"title": "...", "company": "...", ...}' | python3 skills/matcher/scripts/match.py
   ```
   Or use `--offer`:
   ```
   python3 skills/matcher/scripts/match.py --offer '{"title": "...", ...}'
   ```
3. The script reads the CV from `cv/curriculum.md` and calls One API at
   `http://localhost:3001/v1/chat/completions` with model `llama-3.1-8b-instant`
   and temperature 0 for reproducibility (R-MAT-002).
4. Parse the match JSON output and decide:

### Score Interpretation

| Score Range | Action |
|-------------|--------|
| >= 70% | Notify immediately (add to Telegram queue) |
| 50–69% | Flag for CV adaptation (trigger cv_adapter) |
| < 50% | Discard (log only, do not notify) |

### Match Output Format

```json
{
  "score": 87,
  "skills_matched": ["Salesforce CRM", "cross-selling"],
  "skills_missing": ["Kubernetes"],
  "experience_match": true,
  "modality_match": true,
  "salary_in_range": false,
  "adaptation_possible": true,
  "adaptation_focus": ["Mencionar experiencia en ventas consultivas"]
}
```

## Requirements

- R-MAT-001: CV is the sole source of truth for experience
- R-MAT-002: Score must be reproducible (temperature=0)
- R-MAT-003: Skills_matched and skills_missing must be explicitly listed
- R-MAT-004: adaptation_possible triggers CV adapter
- R-MAT-005: Never fabricate or infer experience not in CV
- R-MAT-006: Thresholds configurable in config/search_params.yaml
- R-MAT-007: Scores logged with offer ID for debugging

## Parameters

| Env Variable | Purpose |
|--------------|---------|
| `PICOCLAW_API_KEY` | Bearer token for One API |

## Error handling

- One API unreachable: script exits with code 1
- PICOCLAW_API_KEY not set: script exits with code 1
- CV file missing: script exits with code 1
