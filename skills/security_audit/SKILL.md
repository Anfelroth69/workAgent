---
name: security_audit
description: >-
  Scan the repository for hardcoded secrets, PII exposure, CV privacy issues,
  and sensitive file tracking. Runs as part of preflight validation and blocks
  deploy on CRITICAL findings. Triggers: preflight.py (check #11), manual run via
  `python3 skills/security_audit/scripts/security_scan.py`.
---

# Security Audit Skill

Scans the Pico Claw repository for security issues: hardcoded secrets, PII in tracked files, .gitignore coverage, .dockerignore correctness, CV-in-git tracking, and entrypoint CV loading from env var.

## When to use

- During preflight validation (automatically as check #11)
- Before every deploy (R-SEC-010)
- When troubleshooting CV or secret exposure
- After adding new files with potential secrets

## How to use

Run the scanner directly:
```
python3 skills/security_audit/scripts/security_scan.py
```

It is also invoked automatically via preflight.py:
```
python3 skills/devops_qa/scripts/preflight.py
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed (or only warnings) |
| 1 | CRITICAL finding — deploy blocked |

### Check Categories

1. **Hardcoded secrets** — API keys, tokens, private keys, passwords in tracked files
2. **PII exposure** — Phone numbers, email addresses in tracked files
3. **CV in git** — cv/curriculum.md must NOT be git-tracked
4. **.gitignore** — Must exist and cover cv/, data/, __pycache__, .env
5. **.dockerignore** — Must exclude cv/ to prevent baking into Docker image
6. **Tracked .env files** — .env files must not be in git
7. **Dockerfile CV COPY** — No COPY cv/ in Dockerfile
8. **Entrypoint CV load** — Must load CV from PICOCLAW_CV_BASE64 env var

## Requirements

- R-SEC-001: Security scanner MUST detect hardcoded API keys, tokens, and passwords
- R-SEC-002: Security scanner MUST detect PII (phone, email, address) in tracked files
- R-SEC-003: Security scanner MUST verify that cv/ is excluded from git tracking
- R-SEC-004: Security scanner MUST verify .gitignore exists and covers sensitive files
- R-SEC-005: Security scanner MUST warn about .env or secret files tracked in git
- R-SEC-006: Security scanner MUST warn if sensitive files are world-readable
- R-SEC-007: Security scanner MUST integrate with preflight.py and block deploy on CRITICAL findings
- R-SEC-008: No secrets should be logged during scanning
- R-SEC-009: CV MUST only enter the container via PICOCLAW_CV_BASE64 env var (never via git or Docker build)
- R-SEC-010: Security scan MUST run automatically before every deploy

## Parameters

| Env Variable | Purpose |
|--------------|---------|
| (none) | The scanner reads no env vars; it only scans the filesystem |

## Error handling

- Scanner exits with code 1 if any CRITICAL finding exists
- Scanner exits with code 0 if only warnings (non-blocking)
- If security_scan.py is missing, preflight reports a failure
