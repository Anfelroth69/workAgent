---
name: telegram_bot
description: >-
  Telegram bot for sending job offer notifications to the user and handling
  interactive commands (start, buscar, estado, config, cv, historial, help).
  Listens on port 5003 for HTTP notifications from the orchestrator.
---

# Telegram Bot Skill

Sends job offer notifications to the user via Telegram and handles interactive commands.

## When to use

- After the matcher produces a score >= 50% (notification or adapt-then-notify)
- When the orchestrator needs to send a message to the user
- When the user interacts with the bot via Telegram commands

## How to use

The bot runs as a standalone service managed by supervisord:

```bash
python3 /app/skills/telegram_bot/scripts/bot.py
```

It starts two components in parallel:
1. **Telegram polling** — listens for commands from the user
2. **HTTP server** on port 5003 — receives POST notifications from the orchestrator

### HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/send-message` | Send a Telegram message. Body: `{"chat_id": "...", "text": "..."}` |
| `GET` | `/health` | Returns `{"status": "ok"}` |

### Notification Format

The orchestrator POSTs to `/send-message` with the match result:

```
🎯 MATCH: {score}%
━━━━━━━━━━━━━━━━━━━
💼 {title}
🏢 {company}
📍 {location}
💰 {salary}
🌐 {portal}
⏰ {date_posted}

📌 Skills: {skills_matched}
⚠️ Faltantes: {skills_missing}

🔗 {url}
━━━━━━━━━━━━━━━━━━━
```

### Telegram Commands

| Command | Description | Auth |
|---------|-------------|------|
| `/start` | Welcome message | Any |
| `/buscar` | Manual search trigger (placeholder) | Any |
| `/estado` | Provider health + API key status | Any |
| `/config` | Show current search params | Owner only |
| `/cv` | Send CV file | Owner only |
| `/historial` | Last 7 days offers summary | Any |
| `/help` | List all commands | Any |

## Deduplication

Before sending a notification, the bot checks a SQLite database at `data/seen_offers.db`.
If the offer (url_hash, title_hash) was already sent, it is skipped silently.

## Requirements

- R-TEL-001: Bot token MUST come from TELEGRAM_BOT_TOKEN env var
- R-TEL-002: Owner user ID MUST come from TELEGRAM_OWNER_ID env var
- R-TEL-003: HTTP server MUST run on port 5003
- R-TEL-004: Deduplication MUST use SQLite with composite key (url_hash, title_hash)
- R-TEL-005: Owner-only commands MUST check Telegram user ID against TELEGRAM_OWNER_ID
- R-TEL-006: The bot MUST NOT block: HTTP server runs in background thread, Telegram polling in main thread

## Parameters

| Env Variable | Purpose |
|--------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather |
| `TELEGRAM_OWNER_ID` | Telegram user ID of the owner (numeric) |
