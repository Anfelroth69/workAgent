# Observability

## Current State (Minimal)
The system has no dedicated observability infrastructure. Monitoring relies on:

1. **Render Dashboard**
   - Service status (running/stopped/crashed)
   - Deploy logs (build + start)
   - Resource usage (CPU, memory — free tier shows limited metrics)

2. **Gateway Logs**
   - Fetchable via launcher API: /api/gateway/logs
   - Stored in memory (ephemeral, limited history)
   - Log level: warn (configurable)
   - Contains: LLM call errors, WebSocket events, agent turn lifecycle

3. **entrypoint.sh Output**
   - Printed to stdout during container startup
   - Visible in Render deploy logs
   - Includes: service readiness, config generation, channel setup status

## What's Missing
- No health endpoint for the launcher itself (only /api/auth/status and /api/gateway/status)
- No metrics (request count, latency, error rate)
- No alerting (email, webhook)
- No structured logging (all plain text)
- No crash dumps or core dumps
- No uptime monitoring (Render free tier auto-sleeps)

## Requirements
- R-OBS-001: Gateway logs MUST be retrievable via launcher API
- R-OBS-002: entrypoint.sh MUST log each phase's success/failure
- R-OBS-003: Render health check (/api/status) MUST reflect service health
- R-OBS-004: No PII or secrets in log output
- R-OBS-005: Startup failures MUST be visible in Render deploy logs
