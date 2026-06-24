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

echo "[entrypoint] Starting supervisord..."
/usr/bin/supervisord -c /etc/supervisord.conf &
SUPERVISOR_PID=$!

mkdir -p /root/.picoclaw

echo "[entrypoint] Waiting for One API on port 3001..."
for i in $(seq 1 15); do
  if curl -sf http://127.0.0.1:3001/api/status > /dev/null 2>&1; then
    echo "[entrypoint] One API is ready"
    break
  fi
  if [ "$i" -eq 15 ]; then
    echo "[entrypoint] WARNING: One API not ready, using fallback config"
  fi
  sleep 2
done

MODELS_JSON=""
if [ -n "$PICOCLAW_API_KEY" ]; then
  echo "[entrypoint] Fetching models from One API..."
  MODELS_JSON=$(curl -sf http://127.0.0.1:3001/v1/models \
    -H "Authorization: Bearer $PICOCLAW_API_KEY" 2>/dev/null || true)
fi

if echo "$MODELS_JSON" | grep -q '"id"'; then
  echo "[entrypoint] Generating dynamic config from One API models..."

  MODEL_IDS=$(echo "$MODELS_JSON" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)

  DEFAULT_MODEL=""
  for model_id in $MODEL_IDS; do
    [ -z "$model_id" ] && continue
    [ -z "$DEFAULT_MODEL" ] && DEFAULT_MODEL="$model_id"
  done

  cat > /root/.picoclaw/config.json << CONFIGEOF
{
  "version": 2,
  "agents": {
    "defaults": {
      "model_name": "$DEFAULT_MODEL"
    }
  },
  "model_list": [
CONFIGEOF

  FIRST=true
  for model_id in $MODEL_IDS; do
    [ -z "$model_id" ] && continue
    if [ "$FIRST" = true ]; then
      FIRST=false
    else
      echo "," >> /root/.picoclaw/config.json
    fi
    cat >> /root/.picoclaw/config.json << ENTRYEOF
    {
      "model_name": "$model_id",
      "model": "openai/$model_id",
      "api_base": "http://localhost:3001/v1",
      "api_keys": []
    }
ENTRYEOF
  done

  cat >> /root/.picoclaw/config.json << CONFIGEOF
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
SECEOF
  for model_id in $MODEL_IDS; do
    [ -z "$model_id" ] && continue
    cat >> /root/.picoclaw/.security.yml << SECEOF
  $model_id:0:
    api_keys:
      - "$PICOCLAW_API_KEY"
SECEOF
  done

  echo "[entrypoint] Generated config with models: $(echo $MODEL_IDS | tr '\n' ' ')"
else
  echo "[entrypoint] One API unavailable or PICOCLAW_API_KEY not set, using fallback config"
  cat > /root/.picoclaw/config.json << 'CONFIGEOF'
{
  "version": 2,
  "agents": {
    "defaults": {
      "model_name": "deepseek/deepseek-r1"
    }
  },
  "model_list": [
    {
      "model_name": "deepseek/deepseek-r1",
      "model": "openai/deepseek/deepseek-r1",
      "api_base": "http://localhost:3001/v1",
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

  if [ -n "$PICOCLAW_API_KEY" ]; then
    cat > /root/.picoclaw/.security.yml << SECEOF
model_list:
  deepseek/deepseek-r1:0:
    api_keys:
      - "$PICOCLAW_API_KEY"
SECEOF
  fi
fi

if [ -n "$PICOCLAW_LAUNCHER_TOKEN" ]; then
    echo "[entrypoint] Waiting for launcher on port 18800..."
    for i in $(seq 1 30); do
        if curl -sf http://127.0.0.1:18800/api/auth/status > /dev/null 2>&1; then
            echo "[entrypoint] Launcher is ready"
            break
        fi
        if [ "$i" -eq 30 ]; then
            echo "[entrypoint] WARNING: Launcher did not start, skipping auto-setup"
        fi
        sleep 2
    done

    echo "[entrypoint] Setting launcher password..."
    curl -sf -X POST http://127.0.0.1:18800/api/auth/setup \
        -H "Content-Type: application/json" \
        -d "{\"password\": \"$PICOCLAW_LAUNCHER_TOKEN\", \"confirm\": \"$PICOCLAW_LAUNCHER_TOKEN\"}" \
        > /dev/null 2>&1 && echo "[entrypoint] Password set" || echo "[entrypoint] Password setup failed (maybe already set)"
fi

echo "[entrypoint] All services running"
wait "$SUPERVISOR_PID"
