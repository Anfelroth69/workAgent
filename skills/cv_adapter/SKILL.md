---
name: cv_adapter
description: >-
  Adapt the candidate's CV to better match a specific job offer by reordering
  skills, rewording the summary, and highlighting relevant experience — without
  fabricating anything. Triggered by the matcher when score is 50–69%.
---

# CV Adapter Skill

Generates an offer-specific CV version and cover letter using One API (LLM).

## When to use

- When the matcher returns `adaptation_possible: true` and score is 50-69%
- Before notifying the candidate about an offer that needs CV tailoring

## How to use

Pass the job offer and matcher result as JSON:

```bash
python3 skills/cv_adapter/scripts/adapt.py \
  --offer '{"title": "...", "company": "...", ...}' \
  --match '{"score": 65, "skills_missing": [...], ...}'
```

Or pipe from stdin:

```bash
echo '{"offer": {...}, "match": {...}}' | python3 skills/cv_adapter/scripts/adapt.py
```

## Output

Two files are written to `cv/adapted/`:

- `{sanitized_offer_id}_curriculum.md` — adapted CV
- `{sanitized_offer_id}_cover.md` — cover letter

And JSON is printed to stdout:

```json
{
  "adapted_cv": "cv/adapted/..._curriculum.md",
  "cover_letter_path": "cv/adapted/..._cover.md",
  "changes_made": ["Reordered skills: moved BPO Operations to top", ...],
  "original_cv_hash": "sha256:a1b2c3d4..."
}
```

## Constitutional Rules (hard constraints)

1. **Never fabricate experience** (Rule 9) — cannot add, modify, or extrapolate experience, dates, titles, companies, or certifications
2. **Only REORDER** existing skills to match offer priorities
3. **Only REWORD** the summary/objective section (keep facts intact)
4. **Only HIGHLIGHT** existing experience that relates to missing skills
5. Cover letter can emphasize soft skills and motivation, but must be truthful
6. SHA256 hash of original CV is stored for audit trail

## Requirements

- R-CVA-001: Original CV content must never be modified
- R-CVA-002: SHA256 hash of original CV is computed and stored on every adaptation
- R-CVA-003: Adapted CV must not contain fabricated experience
- R-CVA-004: Cover letter must be truthful
- R-CVA-005: Output paths are always under `cv/adapted/`

## Parameters

| Env Variable | Purpose |
|--------------|---------|
| `PICOCLAW_API_KEY` | Bearer token for One API |

## Error handling

- One API unreachable: script exits with code 1
- PICOCLAW_API_KEY not set: script exits with code 1
- CV file missing: script exits with code 1
- Invalid JSON input: script exits with code 1
