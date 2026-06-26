---
name: devops_qa
description: >-
  Validate project correctness pre-deploy and verify running service post-deploy.
  Acts as an experienced DevOps engineer. Run before every commit and after every deploy.
---

# DevOps QA Skill

Pre-deploy validation and post-deploy smoke testing.

## When to use

- **Before every commit**: run `preflight.py` to catch issues early
- **Before every push to main**: run `preflight.py` — it hits all spec gates
- **After every Render deploy**: run `smoke_test.py` to verify the service is healthy

## How to use

### Pre-flight Check
```bash
python3 skills/devops_qa/scripts/preflight.py
```
Exits 0 if all checks pass, 1 if any critical check fails.

### Smoke Test (after deploy)
```bash
python3 skills/devops_qa/scripts/smoke_test.py --url https://one-api-picoclaw.onrender.com
```
Or with custom URL:
```bash
python3 skills/devops_qa/scripts/smoke_test.py --url http://localhost:3000
```

## Output Format

Both scripts output a clear report:
```
[PASS] check_name — description
[FAIL] check_name — description
[WARN] check_name — description

Result: X passed, Y failed, Z warnings
```

## Error handling

- Pre-flight exits code 1 on ANY [FAIL]
- Smoke test exits code 1 on ANY [FAIL]
- Both print results to stdout, errors to stderr

## Requirements

- R-DQA-001 to R-DQA-024 documented in `specs/16-skill-devops-qa.md`
