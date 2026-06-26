FROM docker.io/sipeed/picoclaw:launcher AS launcher
FROM justsong/one-api:latest AS one-api

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    nginx \
    postgresql-client \
    ca-certificates \
    curl \
    chromium \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir playwright playwright-stealth requests beautifulsoup4 pyyaml python-telegram-bot apscheduler

COPY --from=launcher /usr/local/bin/picoclaw /usr/local/bin/picoclaw
COPY --from=launcher /usr/local/bin/picoclaw-launcher /usr/local/bin/picoclaw-launcher
COPY --from=one-api /one-api /one-api

RUN mkdir -p /etc/nginx/conf.d && \
    ln -sf /etc/nginx/conf.d /etc/nginx/http.d
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY supervisord.conf /etc/supervisord.conf
COPY entrypoint.sh /entrypoint.sh
COPY skills/ /app/skills/
COPY config/ /app/config/
# AGENTS.md injected via env var at runtime for privacy
# CV (curriculum.md) injected via PICOCLAW_CV_BASE64 env var at runtime

RUN chmod +x /entrypoint.sh

EXPOSE 3000

ENTRYPOINT ["/entrypoint.sh"]
