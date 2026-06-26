# System Overview

## Purpose
Autonomous job-scraping AI agent that scrapes job listings, classifies offers, deduplicates, and delivers results via WebSocket. Runs on Render Free Tier as a single-container multi-service monolith.

## Architecture Diagram
```
Internet → Render → Container :3000
                        │
                    nginx reverse proxy
                   ┌──────┼──────────┐
                   │      │          │
               Pico Claw  │    One API
               Launcher   │    (port 3001)
               (port 18800)│    ┌─────┴─────┐
                   │      │    │           │
              Gateway    │  PostgreSQL   LLM APIs
              (port 18790)│  (external)  (Groq)
```

## Components

| Component | Port | Technology | Purpose |
|-----------|------|------------|---------|
| nginx | 3000 (public) | Alpine nginx | Reverse proxy, route traffic, WebSocket upgrades |
| One API | 3001 | justsong/one-api | Unified LLM proxy, channel management, model routing, quotas |
| Pico Claw Launcher | 18800 | sipeed/picoclaw | Agent framework WebUI, session management, gateway control |
| Pico Claw Gateway | 18790 | sipeed/picoclaw | WebSocket endpoint, agent execution, LLM call orchestration |
| PostgreSQL | 5432 (external) | postgres:15| Persistence for One API and agent data |

## Files (9 total, ~820 LOC)

| # | File | LOC | Responsibility |
|---|------|-----|----------------|
| 1 | entrypoint.sh | 283 | Startup orchestration: wait for deps, generate config, create channels, start gateway |
| 2 | nginx.conf | 126 | Reverse proxy: 20+ location blocks routing to internal services |
| 3 | render.yaml | 31 | Render Blueprint: PostgreSQL + Docker web service, env vars |
| 4 | supervisord.conf | 44 | Process supervision: nginx, One API, Pico Claw launcher |
| 5 | Dockerfile | 20 | Multi-stage build: extracts binaries, installs deps |
| 6 | docker-compose.yml | 36 | Local dev: PostgreSQL + app service with env vars |
| 7 | .dockerignore | 4 | Excludes unnecessary files from Docker build context |
| 8 | README.md | 134 | Spanish-language project documentation |
| 9 | POST_DEPLOYMENT.md | 141 | Post-deployment setup checklist |

## Data Flow (Message Send)
```
User WebSocket → /pico/ws → nginx → Launcher :18800
  → Gateway :18790 → nginx → One API :3001
  → Groq API → response → One API → nginx → Gateway
  → Launcher → nginx → User WebSocket
```

## Key Constraints
- Render Free Tier: 512MB RAM, auto-sleep after inactivity, ephemeral filesystem
- All services must start within container startup window
- PostgreSQL is external (managed Render DB)
- Groq is the primary LLM provider (model: llama-3.1-8b-instant via model_mapping)
- No metrics or alerting infrastructure
