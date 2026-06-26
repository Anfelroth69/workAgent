# Security Audit Skill

## Current State (Minimal)
The system has no dedicated security auditing. Sensitive information may be inadvertently tracked or exposed:

1. **Secrets in code** — No automated detection of hardcoded API keys, tokens, or passwords
2. **PII exposure** — CV and candidate info may be git-tracked
3. **Build-time secrets** — CV could be baked into Docker images if not properly excluded
4. **File permissions** — No checks for world-readable sensitive files
5. **Deploy gate** — No security check blocks deploys on critical findings

## What's Missing
- No automated secret scanning
- No PII detection in tracked files
- No verification that `.gitignore` properly covers PII
- No deploy-blocking security gate
- No CV-in-Docker-image detection
- No `.dockerignore` validation
- No entrypoint env-var-based CV loading validation

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
