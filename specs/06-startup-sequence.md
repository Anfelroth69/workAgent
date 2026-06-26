# Startup Sequence

## Entrypoint File: entrypoint.sh (~296 LOC)

## Phase Diagram
```
entrypoint.sh
├── 1. Wait for PostgreSQL (30 retries × 2s)
├── 2. Start supervisord (nginx, One API, Launcher)
├── 3. Wait for One API :3001 (15 retries × 2s)
├── 4. Fetch models from One API /v1/models
│   ├── Success → Dynamic config generation
│   │   ├── Filter modelperm- entries
│   │   ├── Select default model (prefer *instant*|*versatile*)
│   │   ├── Generate config.json (model_list + channel_list + gateway)
│   │   ├── Delete stale .security.yml
│   │   └── Generate .security.yml from filtered model list
│   └── Failure → Fallback config (hardcoded llama-3.1-8b-instant)
├── 5. Wait for Launcher :18800 (30 retries × 2s)
├── 6. Set launcher password (idempotent)
├── 7. Login to launcher → LAUNCHER_COOKIE
├── 8. Configure pico channel (token setup)
├── 9. Setup Groq channel in One API
│   ├── Login to One API (root/123456)
│   ├── Check if Groq channel exists
│   │   ├── Exists → skip
│   │   └── Not exists → POST new channel
│   └── Cleanup cookie
├── 10. Validate model reachability in One API (5 retries, backoff: 2s,4s,6s,8s,10s)
│   ├── Reachable → proceed to gateway start
│   └── Unreachable → log error, skip gateway start
├── 11. Start gateway (10 retries × 2s, only if model reachable)
└── 12. Wait for supervisord
```

## Decision Points

### D1: One API Reachability
- PASS: curl to :3001/api/status returns 200
- FAIL: Use fallback config (single model, no channel setup)
- RETRY: 15 attempts, 2s apart

### D2: Model List Available
- PASS: /v1/models response contains "id" field
- FAIL: Use fallback config
- FILTER: grep -v '^modelperm-' removes One API permission entries

### D3: Launcher Ready
- PASS: /api/auth/status returns 200
- FAIL: Skip all launcher-dependent operations (auth, pico setup, gateway start)
- RETRY: 30 attempts, 2s apart

### D4: One API Admin Login (Groq setup)
- PASS: /api/user/login returns cookie
- FAIL: Skip Groq channel creation; gateway may still start

### D5: Model Reachability (NEW)
- PASS: Default model found in /v1/models response
- FAIL: Log error with troubleshooting steps, skip gateway start entirely
- RETRY: 5 attempts with exponential backoff (2s, 4s, 6s, 8s, 10s)
- GATE: This is the enforcement point for Constitution Rule 4

### D6: Gateway Start
- PASS: /api/gateway/start returns 200
- FAIL: Log warning, continue (gateway not running)
- RETRY: 10 attempts, 2s apart

## Requirements
- R-SS-001: PostgreSQL MUST be reachable before any service starts
- R-SS-002: supervisord MUST be started in background (not blocking)
- R-SS-003: Dynamic config generation MUST filter modelperm- entries
- R-SS-004: .security.yml MUST be freshly generated (not appended to stale file)
- R-SS-005: Default model selection MUST prefer *instant*|*versatile* models
- R-SS-006: Groq channel creation MUST check for existing channel first (idempotent)
- R-SS-007: Gateway start MUST verify model reachability (Constitution Rule 4)
- R-SS-008: Each retry loop MUST have a maximum attempt count
- R-SS-009: Fallback config MUST still work if One API is unreachable
- R-SS-010: Model validation retries MUST use increasing backoff, not fixed interval
