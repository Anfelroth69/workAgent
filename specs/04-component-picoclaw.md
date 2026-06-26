# Component: Pico Claw (Launcher + Gateway)

## Technology
sipeed/picoclaw:launcher — Go-based AI agent framework.

## Launcher (port 18800)
WebUI and API server for managing agents, sessions, and the gateway.

### Auth Flow
```
Deploy → entrypoint.sh sets password via /api/auth/setup
       → entrypoint.sh logs in via /api/auth/login
       → LAUNCHER_COOKIE saved for subsequent API calls
```

### API Endpoints (via Launcher)
| Endpoint | Purpose |
|----------|---------|
| /api/auth/setup | Initial password setup |
| /api/auth/login | Login, returns cookie |
| /api/auth/status | Health check |
| /api/gateway/status | Gateway process status |
| /api/gateway/start | Start gateway process |
| /api/gateway/stop | Stop gateway process |
| /api/gateway/logs | Fetch gateway logs |
| /api/pico/setup | Configure pico WebSocket channel |

## Gateway (port 18790)
WebSocket server that executes AI agent turns. Controlled via launcher API (/api/gateway/start, /api/gateway/stop, /api/gateway/status).

### Gateway Start Validation
Before the gateway starts, entrypoint.sh polls One API `/v1/models` to verify the default model is reachable. This prevents silent failures where the gateway boots but drops all messages.
- Retries: 5 attempts with exponential backoff (2s, 4s, 6s, 8s, 10s)
- If unreachable: gateway is NOT started, error logged with troubleshooting steps
- Enforcement: Constitution Rule 4 (HARD)

### Config File: /root/.picoclaw/config.json
Generated dynamically by entrypoint.sh. Two modes:

**Dynamic Mode** (One API reachable):
- model_list populated from One API /v1/models
- Default model: first model matching *instant*|*versatile*, or first model in list
- Each model entry: OpenAI-compatible with api_base = localhost:3001/v1

**Fallback Mode** (One API unreachable):
- Single model: llama-3.1-8b-instant
- api_base = localhost:3001/v1

### Security File: /root/.picoclaw/.security.yml
Generated alongside config.json. Lists each model with its allowed API key.

### WebSocket Channel (pico)
- Channel type: pico
- Token-authenticated connections
- Streaming enabled
- Ping interval: 30s
- Read timeout: 60s
- Write timeout: 10s
- Max connections: 100

## Requirements
- R-PC-001: Gateway config MUST be regenerated from One API /v1/models on every deploy
- R-PC-002: .security.yml MUST be deleted before regeneration (Constitution Rule 2)
- R-PC-003: Default model selection prefers *instant*|*versatile* patterns, then first available
- R-PC-004: Fallback mode MUST use a hardcoded reachable model (llama-3.1-8b-instant)
- R-PC-005: Launcher API calls MUST use cookie-based auth
- R-PC-006: Gateway MUST NOT start if the default model is unreachable (Constitution Rule 4)
- R-PC-007: Gateway logs are fetched via launcher API (no direct file access)
- R-PC-008: modelperm- entries from /v1/models MUST be filtered out
