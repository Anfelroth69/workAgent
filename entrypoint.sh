#!/bin/sh
set -e

HOST_PORT=$(echo "$SQL_DSN" | sed 's/^postgres:\/\/[^@]*@//' | cut -d/ -f1)
case "$HOST_PORT" in
  *:*) DB_HOST=$(echo "$HOST_PORT" | cut -d: -f1)
       DB_PORT=$(echo "$HOST_PORT" | cut -d: -f2) ;;
  *)   DB_HOST="$HOST_PORT"
       DB_PORT=5432 ;;
esac

echo "[entrypoint] Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
for i in $(seq 1 30); do
  if pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
    echo "[entrypoint] PostgreSQL is ready"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "[entrypoint] ERROR: PostgreSQL not available after 60s"
    exit 1
  fi
  sleep 2
done

echo "[entrypoint] Creating Pico Claw configuration..."
mkdir -p /root/.picoclaw

cat > /root/.picoclaw/config.json << 'CONFIGEOF'
{
  "version": 2,
  "agents": {
    "defaults": {
      "model_name": "gpt-4o-mini"
    }
  },
  "model_list": [
    {
      "model_name": "gpt-4o-mini",
      "model": "openai/gpt-4o-mini",
      "api_base": "http://localhost:3000/v1",
      "api_keys": []
    }
  ],
  "gateway": {
    "host": "127.0.0.1",
    "port": 18790,
    "log_level": "warn"
  }
}
CONFIGEOF

cat > /root/.picoclaw/.security.yml << SECEOF
model_list:
  gpt-4o-mini:0:
    api_keys:
      - "${PICOCLAW_API_KEY}"
SECEOF

echo "[entrypoint] Rendering nginx config..."
export PORT="${PORT:-3000}"
envsubst '${PORT}' < /etc/nginx/http.d/default.conf.template > /etc/nginx/http.d/default.conf

echo "[entrypoint] Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisord.conf
