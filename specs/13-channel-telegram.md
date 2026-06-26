# Channel: Telegram Bot

## Purpose
Deliver job notifications and accept user commands via Telegram.

## Connection
- Pico Claw native Telegram channel (built-in) OR
- Python telegram bot running alongside Pico Claw
- Webhook: `https://api.telegram.org/bot<TOKEN>/setWebhook`
- Bot token stored in One API / env var (never in code)

## Commands

| Command | Description | Auth |
|---------|-------------|------|
| /buscar | Trigger manual search now | Any user |
| /estado | API key status + provider health | Any user |
| /config | View current search params | Owner only |
| /cv | Return current CV as file | Owner only |
| /historial | Last 7 days offers summary | Any user |
| /adaptar_[id] | Generate adapted CV for offer ID | Owner only |
| /rechazar_[id] | Reject an adapted CV | Owner only |

## Message Format (Match)
```
🎯 MATCH: 87%
━━━━━━━━━━━━━━━━━━━
💼 Senior Python Developer
🏢 Acme Corp
📍 Remote - Spain
💰 50k-70k EUR
🌐 LinkedIn
⏰ Publicado: hace 3h

📌 Skills: Python, Docker, FastAPI
⚠️ Faltantes: Kubernetes

🔗 Ver oferta
━━━━━━━━━━━━━━━━━━━
📄 ¿Adaptar CV? → /adaptar_abc123
```

## Deduplication
- Offers tracked by (URL_hash, title_hash) composite key
- Stored in SQLite (`data/seen_offers.db`)
- Never notify twice for same offer
- Cleanup: remove entries older than 30 days

## Requirements
- R-TG-001: Bot token MUST NOT be hardcoded — env var only
- R-TG-002: All commands MUST respond within 5s (ack immediate, process async)
- R-TG-003: Notification format MUST be consistent (template in spec)
- R-TG-004: Deduplication MUST prevent double-notification
- R-TG-005: /estado command MUST show real-time provider health from One API
- R-TG-006: Owner-only commands MUST validate user ID against config
- R-TG-007: Messages MUST be truncatable (max 4096 chars for Telegram)
