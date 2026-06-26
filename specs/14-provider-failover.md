# Providers: Failover & Multi-Provider

## Current State
Only Groq is configured. Vision requires multiple providers to avoid single-provider downtime.

## Target Providers

| Provider | Type | Free Tier Limit | Priority | Status |
|----------|------|----------------|:--------:|:------:|
| Groq | Primary | 6000 TPM, 6000 RPD | P1 | ✅ Active |
| OpenRouter | Failover | Credit-based | P1 | ❌ Not configured |
| Google Gemini | Failover | 60 RPM | P2 | ❌ Not configured |
| Mistral AI | Failover | 1 RPM (free) | P2 | ❌ Not configured |
| Cohere | Tertiary | 100 TPM (free) | P3 | ❌ Not configured |

## Failover Logic

```
Request → One API → Primary (Groq)
                   → 429/413/5xx → Rotate to OpenRouter
                                  → 429/5xx → Rotate to Gemini
                                             → All failed → Log error, queue retry
```

### Retry Policy
- 429 (rate limited): Wait `Retry-After` header, retry up to 3× per provider
- 413 (too large): Immediate provider rotation (no retry on same provider)
- 5xx: Retry 2× with 5s backoff, then rotate
- All providers exhausted: Queue job for next cycle

## One API Channel Configuration
Each provider gets its own One API channel:
- Channel per provider with type=1 (OpenAI-compatible)
- Group routing: Pico Claw → group "default" → primary channels
- Weight-based distribution (primary gets higher weight)

## Requirements
- R-PR-001: Each provider MUST have its own One API channel entry
- R-PR-002: Primary provider failure MUST auto-rotate to next available
- R-PR-003: 413 errors MUST NOT retry on same provider (rotation only)
- R-PR-004: 429 errors MUST respect Retry-After header
- R-PR-005: All rotations MUST be logged with provider name, error, timestamp
- R-PR-006: Provider health MUST be exposed via /estado Telegram command
- R-PR-007: New providers MUST have a spec section before integration
