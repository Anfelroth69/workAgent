FROM docker.io/sipeed/picoclaw:launcher AS launcher
FROM justsong/one-api:latest AS one-api

FROM alpine:3.21

RUN apk add --no-cache supervisor postgresql-client nginx ca-certificates tzdata curl \
    python3 py3-pip py3-yaml py3-beautifulsoup4 py3-requests \
    chromium

RUN pip3 install --break-system-packages --no-cache-dir playwright playwright-stealth

COPY --from=launcher /usr/local/bin/picoclaw /usr/local/bin/picoclaw
COPY --from=launcher /usr/local/bin/picoclaw-launcher /usr/local/bin/picoclaw-launcher
COPY --from=one-api /one-api /one-api

COPY nginx.conf /etc/nginx/http.d/default.conf
COPY supervisord.conf /etc/supervisord.conf
COPY entrypoint.sh /entrypoint.sh
COPY skills/ /app/skills/
COPY cv/ /app/cv/
COPY config/ /app/config/
COPY AGENTS.md /app/AGENTS.md

RUN chmod +x /entrypoint.sh

EXPOSE 3000

ENTRYPOINT ["/entrypoint.sh"]
