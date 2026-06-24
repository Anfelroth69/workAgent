FROM docker.io/sipeed/picoclaw:launcher AS launcher
FROM justsong/one-api:latest AS one-api

FROM alpine:latest

RUN apk add --no-cache supervisor postgresql-client nginx ca-certificates tzdata curl

COPY --from=launcher /usr/local/bin/picoclaw /usr/local/bin/picoclaw
COPY --from=launcher /usr/local/bin/picoclaw-launcher /usr/local/bin/picoclaw-launcher
COPY --from=one-api /one-api /one-api

COPY nginx.conf.template /etc/nginx/http.d/default.conf.template
COPY supervisord.conf /etc/supervisord.conf
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 3000

ENTRYPOINT ["/entrypoint.sh"]
