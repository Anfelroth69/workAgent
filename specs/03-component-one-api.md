# Component: One API

## Technology
justsong/one-api:latest — Go-based unified LLM proxy with load balancing, channel management, and quota system.

## Port
3001 (internal only, proxied through nginx)

## Admin Interface
- URL: https://one-api-picoclaw.onrender.com/
- Default credentials: username=`root`, password=`123456`

## Channels

| ID | Name | Type | Status | Provider | Base URL |
|----|------|------|--------|----------|----------|
| 4 | Groq | 1 (OpenAI) | 1 (Enabled) | Groq | https://api.groq.com/openai |
| 5 | Groq | 1 (OpenAI) | 1 (Enabled) | Groq | https://api.groq.com/openai |
| 6 | Groq | 1 (OpenAI) | 1 (Enabled) | Groq | https://api.groq.com/openai |

**Note**: Multiple Groq channels exist due to historical bug in idempotent channel creation (see Constitution Rule 1).

### Groq Channel Configuration
- Type: 1 (OpenAI-compatible)
- Models: llama-3.1-8b-instant, llama-3.3-70b-versatile, deepseek-r1, deepseek/deepseek-r1
- Model Mapping: deepseek-r1 → llama-3.3-70b-versatile, default → llama-3.3-70b-versatile
- API Key: set via GROQ_API_KEY env var

## Tokens

| ID | Key | Status | Quota | Models Restriction |
|----|-----|--------|-------|-------------------|
| 1 | root-token-cambiar-en-dashboard | Enabled | Unlimited | deepseek/deepseek-r1 (**stale**) |
| 2 | jHCqzNM7HZXY1zVY0a06Cd83D9B4492790719d3fE30b4fB3 | Enabled | Unlimited | None |

**Note**: Token ID 1 has a stale model restriction. The gateway uses PICOCLAW_API_KEY env var which maps to one of these tokens via entrypoint.sh.

## Model Routing Flow
```
Client Request (model: llama-3.1-8b-instant)
  → nginx /api/ → One API
  → Channel matching (model in channel's models list)
  → Model mapping applied (llama-3.1-8b-instant → llama-3.3-70b-versatile)
  → Groq API request (model: llama-3.3-70b-versatile)
  → Response back through chain
```

## Requirements
- R-OA-001: Channel creation MUST be idempotent (check before POST)
- R-OA-002: Model mapping MUST be a bijection (one incoming → one outgoing)
- R-OA-003: Tokens used for /v1/chat/completions MUST have unlimited_quota
- R-OA-004: /v1/models endpoint MUST only list models from enabled channels
- R-OA-005: Channel status=1 means enabled; PUT does NOT change status reliably (known One API behavior)
