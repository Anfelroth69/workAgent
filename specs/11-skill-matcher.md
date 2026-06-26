# Skill: Matcher

## Purpose
Compare scraped job offers against the CV (curriculum.md) and compute a semantic match score.

## Input
- Job offer (normalized format from scrapers)
- CV: `cv/curriculum.md` (Markdown)

## Output
```yaml
match:
  score: 87                    # 0-100
  skills_matched:
    - Python
    - Docker
    - FastAPI
  skills_missing:
    - Kubernetes
  experience_match: true       # Required vs available years
  modality_match: true         # Remote vs Remote
  salary_in_range: false       # If salary available
  adaptation_possible: true    # Score > 50% but < threshold?
  adaptation_focus:            # What to highlight if adapting
    - Kubernetes experience
    - Cloud certifications
```

## Matching Algorithm

1. **Semantic comparison**: LLM compares CV sections to offer requirements
2. **Score breakdown**:
   - Technical skills match: 50% weight
   - Experience level: 20% weight
   - Modality/location: 15% weight
   - Industry/sector: 10% weight
   - Language requirements: 5% weight
3. **Thresholds**:
   - Score >= 70%: Auto-notify
   - Score 50-69%: Flag as "possible adaptation"
   - Score < 50%: Discard (log only)

## Requirements
- R-MAT-001: Matcher MUST use the CV as the sole source of truth for experience
- R-MAT-002: Score MUST be reproducible (same CV + offer = same score)
- R-MAT-003: Skills_matched and skills_missing MUST be explicitly listed
- R-MAT-004: Adaptation_possible flag MUST trigger CV adapter if True
- R-MAT-005: Matcher MUST NOT fabricate or infer experience not in CV
- R-MAT-006: Thresholds MUST be configurable in `config/search_params.yaml`
- R-MAT-007: Scores MUST be logged with offer ID for debugging
