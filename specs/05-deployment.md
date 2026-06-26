# Deployment

## Platform
Render.com, Free Tier

## Files

### render.yaml (Blueprint)
Defines:
- PostgreSQL database (one-api-db, free plan)
- Docker web service (one-api-picoclaw, free plan, oregon region)
- Health check: /api/status
- Env vars (7 total)

### Dockerfile (Multi-stage)
```
Stage 1: sipeed/picoclaw:launcher → extract picoclaw + picoclaw-launcher
Stage 2: justsong/one-api:latest → extract /one-api binary
Stage 3: alpine:latest → install deps, combine binaries, copy configs
```

### docker-compose.yml (Local dev)
- PostgreSQL 15-alpine with health check
- App service with all env vars
- Port mapping: 3000:3000

### .dockerignore
Excludes .git, .gitignore, docker-compose.yml, README.md

## Environment Variables

| Variable | Source | Sync | Purpose |
|----------|--------|------|---------|
| SQL_DSN | Render DB | auto | PostgreSQL connection string |
| SESSION_SECRET | Generate | false (manual) | One API session secret |
| INITIAL_ROOT_TOKEN | Generate | false (manual) | One API initial root token (not currently used) |
| PICOCLAW_API_KEY | Generate | false (manual) | Gateway API key for One API |
| PICOCLAW_LAUNCHER_TOKEN | Generate | false (manual) | Launcher admin password |
| GROQ_API_KEY | Generate | false (manual) | Groq API key for LLM access |
| PORT | Fixed | auto | Render-assigned port (3000) |

## Requirements
- R-DEP-001: Every LLM provider API key MUST have a corresponding env var in render.yaml
- R-DEP-002: render.yaml MUST have sync:false for secrets (never auto-sync from code)
- R-DEP-003: Dockerfile MUST use multi-stage build to minimize image size (~30MB)
- R-DEP-004: Health check path MUST return 200 within Render's timeout
- R-DEP-005: PostgreSQL credentials in render.yaml and docker-compose.yml MUST match
- R-DEP-006: docker-compose.yml uses different DSN than render.yaml (local vs production)
