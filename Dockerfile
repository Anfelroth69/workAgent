FROM justsong/one-api:latest

USER root

RUN apk add --no-cache supervisor wget postgresql-client

RUN wget -qO- https://github.com/sipeed/picoclaw/releases/latest/download/picoclaw_Linux_x86_64.tar.gz \
    | tar -xz -C /usr/local/bin/

COPY supervisord.conf /etc/supervisord.conf
COPY entrypoint.sh /entrypoint.sh
COPY picoclaw-gateway.sh /usr/local/bin/picoclaw-gateway.sh

RUN chmod +x /entrypoint.sh /usr/local/bin/picoclaw-gateway.sh

EXPOSE 3000

ENTRYPOINT ["/entrypoint.sh"]
