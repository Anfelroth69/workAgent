# Component: nginx

## Spec File: nginx.conf (126 LOC)

## Purpose
Reverse proxy running on port 3000 (Render-assigned $PORT). Routes external traffic to the correct internal service.

## Route Table

### Routes to Pico Claw Launcher (127.0.0.1:18800)

| Location | Purpose | Auth | WebSocket |
|----------|---------|------|-----------|
| /api/auth/ | Login, session management | No | No |
| /api/config | Pico Claw configuration API | Cookie | No |
| /api/models | List available models | Cookie | No |
| /api/gateway/ | Gateway start/stop/status | Cookie | No |
| /api/channels/ | Channel management | Cookie | No |
| /api/system/ | System management | Cookie | No |
| /api/pico/ | Pico channel setup | Cookie | No |
| /picoclaw/ | WebUI interface | Cookie | Yes (upgrade) |
| /pico/ | WebSocket and REST for agent chat | Cookie | Yes (upgrade) |
| /launcher-setup | Initial password setup | No | No |
| /launcher-login | Login page | No | No |
| /static/ | Static assets (CSS, JS) | No | No |
| /assets/ | Additional assets | No | No |

### Routes to One API (127.0.0.1:3001)

| Location | Purpose | Auth | Notes |
|----------|---------|------|-------|
| /api/status | Health check | No | Render health check path |
| /api/ | One API REST API (tokens, channels, models) | Cookie | Fallback catch-all |
| / | One API Admin UI | Cookie | Root path |

### Routes to Gateway (127.0.0.1:18790)

| Location | Purpose | Auth | WebSocket |
|----------|---------|------|-----------|
| /pico-gateway/ | Gateway WebSocket traffic | Token | Yes (upgrade) |

## WebSocket Configuration
All WebSocket-supporting locations include:
```
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

## Requirements

- R-NGX-001: Route ordering matters — specific routes before generic catch-alls (/api/ before /)
- R-NGX-002: All internal routes must set Host/X-Real-IP/X-Forwarded-For headers
- R-NGX-003: WebSocket endpoints must have Upgrade/Connection headers
- R-NGX-004: /api/status must return 200 for Render health checks
- R-NGX-005: /pico-gateway/ must rewrite path from /pico-gateway/ to /pico/
- R-NGX-006: /picoclaw/ must rewrite path from /picoclaw/ to /
- R-NGX-007: No external service routes (all proxy_pass to localhost)
