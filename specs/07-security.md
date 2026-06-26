# Security

## Authentication Flows

### External Users → Pico Claw WebSocket
- WebSocket connections to /pico/ws require a valid session cookie
- Session obtained via /api/auth/login (password: PICOCLAW_LAUNCHER_TOKEN)
- Gateway uses pico channel token for internal auth

### Internal Services → One API
- API calls use Bearer token (PICOCLAW_API_KEY)
- Token must have unlimited_quota: true
- Token maps to One API token ID 2 (unrestricted models)

### entrypoint.sh → One API Admin
- Uses hardcoded root/123456 credentials for API management
- Session cookie obtained via /api/user/login
- Used only for Groq channel setup during deploy

## Token Inventory

| System | Token | Storage | Purpose |
|--------|-------|---------|---------|
| One API Root | 123456 (password) | Hardcoded in entrypoint.sh | Admin API access |
| One API Token 1 | root-token-cambiar-en-dashboard | One API DB | (stale, restricted to deepseek/deepseek-r1) |
| One API Token 2 | `[REDACTED - set via PICOCLAW_API_KEY env var]` | One API DB (set in Render dashboard) | Primary LLM access |
| Pico Claw Launcher | PICOCLAW_LAUNCHER_TOKEN env var | Render env vars | Launcher WebUI + API auth |
| Pico Channel | PICO_TOKEN (derived from launcher token) | Generated at runtime | WebSocket channel auth |
| Groq | GROQ_API_KEY env var | Render env vars | LLM API access |

## Security Model
- No TLS between internal services (all localhost)
- nginx terminates external TLS (Render-managed)
- .security.yml restricts which API keys can use which models in gateway
- One API channels can be restricted by model group

## Known Issues
- Token ID 1 has stale model restriction to deepseek/deepseek-r1 (no longer used)
- Token ID 2 has no model restriction (overly permissive)
- Root password (123456) is hardcoded and never rotated
- GROQ_API_KEY stored as render.yaml env var with sync:false

## Requirements
- R-SEC-001: API keys used for LLM calls MUST have unlimited_quota
- R-SEC-002: .security.yml MUST be regenerated fresh on every deploy
- R-SEC-003: No secrets should be logged during startup
- R-SEC-004: Render env vars with sensitive values MUST use sync:false
- R-SEC-005: Tokens with stale model restrictions MUST be cleaned up
