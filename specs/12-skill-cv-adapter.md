# Skill: CV Adapter

## Purpose
Generate a tailored version of the CV for a specific offer when the match is close but not perfect (50-69%).

## Input
- Original CV: `cv/curriculum.md`
- Matcher output (skills_matched, skills_missing, adaptation_focus)
- Target offer (normalized format)

## Output
```yaml
adapted_cv:
  path: "cv/adapted/offer_123_curriculum.md"
  cover_letter_path: "cv/adapted/offer_123_cover.md"
  changes_made:
    - "Reordered skills: moved Python to top"
    - "Updated summary to highlight Docker experience"
    - "Added Kubernetes learning note"
  original_cv_hash: sha256:...  # For audit trail
```

## Rules (CONSTITUTION HARD — never override)
1. NEVER add experience you don't have
2. NEVER change dates, titles, or company names
3. Only REORDER existing skills to match offer priorities
4. Only REWORD the summary/objective section (keep facts intact)
5. Only HIGHLIGHT existing experience that relates to missing skills (e.g., "I used Docker Compose → shows container knowledge relevant to Kubernetes")
6. Cover letter can emphasize soft skills and motivation, but must be truthful

## Requirements
- R-CV-001: CV adapter MUST be invoked only when match score is 50-69%
- R-CV-002: Every adapted CV MUST store the original CV hash for audit
- R-CV-003: Cover letter MUST be generated alongside adapted CV
- R-CV-004: Changes_made MUST list every modification for transparency
- R-CV-005: Adapted CV path MUST include the offer ID for traceability
- R-CV-006: User MUST be able to reject an adapted CV via Telegram
- R-CV-007: NEVER fabricate experience (Constitution Rule 9)
