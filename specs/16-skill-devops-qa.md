# Skill: DevOps QA

## Purpose
Validate the entire project for correctness before deploying, and verify the running service after deploy. Acts as an experienced DevOps engineer — catches common issues early.

## Pre-flight Validation (`preflight.py`)

### Python Syntax Check
- R-DQA-001: ALL `.py` files in `skills/` MUST parse without syntax errors
- R-DQA-002: Script MUST exit with code 1 if any Python file has syntax errors

### YAML Validity
- R-DQA-003: ALL `.yaml`/`.yml` files in `config/` MUST be valid YAML
- R-DQA-004: ALL `.yaml`/`.yml` files in `.github/` MUST be valid YAML
- R-DQA-005: `render.yaml` MUST be valid YAML

### Dockerfile
- R-DQA-006: `Dockerfile` MUST exist
- R-DQA-007: `Dockerfile` MUST reference valid base images

### Shell Script Check
- R-DQA-008: `entrypoint.sh` MUST parse with `sh -n` (syntax check)
- R-DQA-009: All `config/*.sh` files MUST parse with `sh -n`

### Spec Coverage
- R-DQA-010: All spec files `specs/01-*.md` through `specs/16-*.md` MUST exist
- R-DQA-011: Total R- requirements across ALL specs MUST be >= 65

### Constitution
- R-DQA-012: `.specify/memory/constitution.md` MUST exist with >= 12 rules
- R-DQA-013: Anti-fabrication clause (Rule 9) MUST be present

### Render Config Completeness
- R-DQA-014: Every `$*_API_KEY` and `$*_TOKEN` in `entrypoint.sh` MUST have a corresponding entry in `render.yaml`
- R-DQA-015: `render.yaml` MUST be valid

### No Stale Artifacts
- R-DQA-016: No `__pycache__` directories SHOULD be present (warning)

### Skill Integrity
- R-DQA-017: Every directory in `skills/` MUST contain `SKILL.md`
- R-DQA-018: Every implemented skill MUST have a `scripts/` directory

### CV Integrity
- R-DQA-019: `cv/curriculum.md` MUST exist and be non-empty

## Post-deploy Smoke Test (`smoke_test.py`)

### Health Check
- R-DQA-020: Service health endpoint (`/api/status`) MUST return 200

### One API Reachability
- R-DQA-021: One API `/v1/models` MUST return at least one model

### Gateway Status
- R-DQA-022: Gateway status endpoint MUST return `running`

## Pre-commit Hook
- R-DQA-023: `preflight.py` SHOULD run before every commit
- R-DQA-024: If `preflight.py` exits with code 1, commit SHOULD be blocked
