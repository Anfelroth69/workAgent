#!/bin/sh
set -e

PICO_TOKEN="${PICOCLAW_LAUNCHER_TOKEN:-picoclaw-default-token}"

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

  MODEL_IDS=$(echo "$MODELS_JSON" | grep -o '"id":"[^"]*"' | cut -d'"' -f4 | grep -v '^modelperm-' | sort -u)

  DEFAULT_MODEL=""
  for model_id in $MODEL_IDS; do
    [ -z "$model_id" ] && continue
    case "$model_id" in
      *instant*|*versatile*) DEFAULT_MODEL="$model_id" ;;
    esac
  done
  if [ -z "$DEFAULT_MODEL" ]; then
    for model_id in $MODEL_IDS; do
      [ -z "$model_id" ] && continue
      [ -z "$DEFAULT_MODEL" ] && DEFAULT_MODEL="$model_id"
    done
  fi

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
      "api_keys": ["$PICOCLAW_API_KEY"]
    }
ENTRYEOF
  done

  cat >> /root/.picoclaw/config.json << CONFIGEOF
  ],
  "channel_list": {
    "pico": {
      "enabled": true,
      "type": "pico",
      "settings": {
        "token": "$PICO_TOKEN",
        "streaming": { "enabled": true },
        "ping_interval": 30,
        "read_timeout": 60,
        "write_timeout": 10,
        "max_connections": 100
      }
    }
  },
  "gateway": {
    "host": "127.0.0.1",
    "port": 18790,
    "log_level": "warn"
  }
}
CONFIGEOF

  rm -f /root/.picoclaw/.security.yml
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

  FALLBACK_API_KEYS="[]"
  [ -n "$PICOCLAW_API_KEY" ] && FALLBACK_API_KEYS='["'$PICOCLAW_API_KEY'"]'

  cat > /root/.picoclaw/config.json << CONFIGEOF
{
  "version": 2,
  "agents": {
    "defaults": {
      "model_name": "llama-3.1-8b-instant"
    }
  },
  "model_list": [
    {
      "model_name": "llama-3.1-8b-instant",
      "model": "openai/llama-3.1-8b-instant",
      "api_base": "http://localhost:3001/v1",
      "api_keys": $FALLBACK_API_KEYS
    }
  ],
  "channel_list": {
    "pico": {
      "enabled": true,
      "type": "pico",
      "settings": {
        "token": "$PICO_TOKEN",
        "streaming": { "enabled": true },
        "ping_interval": 30,
        "read_timeout": 60,
        "write_timeout": 10,
        "max_connections": 100
      }
    }
  },
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
  llama-3.1-8b-instant:0:
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

echo "[entrypoint] Logging into launcher..."
LAUNCHER_COOKIE=$(mktemp)
if curl -sf -c "$LAUNCHER_COOKIE" -X POST http://127.0.0.1:18800/api/auth/login \
    -H "Content-Type: application/json" \
    -d "{\"password\": \"$PICOCLAW_LAUNCHER_TOKEN\"}" \
    > /dev/null 2>&1; then
    echo "[entrypoint] Launcher login successful"
else
    echo "[entrypoint] Launcher login failed (may need initial setup)"
    LAUNCHER_COOKIE=""
fi

echo "[entrypoint] Configuring pico channel..."
if [ -n "$LAUNCHER_COOKIE" ] && curl -sf -b "$LAUNCHER_COOKIE" -X POST http://127.0.0.1:18800/api/pico/setup \
    -H "Content-Type: application/json" \
    -d "{\"token\": \"$PICO_TOKEN\"}" \
    > /dev/null 2>&1; then
    echo "[entrypoint] Pico channel configured"
else
    echo "[entrypoint] Pico setup failed (may need auth or already configured)"
fi

echo "[entrypoint] Setting up Groq channel in One API..."
if [ -n "$GROQ_API_KEY" ]; then
    # Login to One API as admin
    ONEAPI_COOKIE=$(mktemp)
    if curl -sf -c "$ONEAPI_COOKIE" -X POST "http://127.0.0.1:3001/api/user/login" \
        -H "Content-Type: application/json" \
        -d '{"username":"root","password":"123456"}' \
        > /dev/null 2>&1; then
        echo "[entrypoint] One API admin login successful"
        # Check if Groq channel already exists
        EXISTING=$(curl -sf -b "$ONEAPI_COOKIE" "http://127.0.0.1:3001/api/channel/" 2>/dev/null || echo "")
        GROQ_EXISTS=$(echo "$EXISTING" | grep -o '"id":[0-9]*,"type":[0-9]*,"name":"Groq"' | grep -o 'id":[0-9]*' | grep -o '[0-9]*' || echo "")
        if [ -n "$GROQ_EXISTS" ]; then
            echo "[entrypoint] Groq channel already exists (ID: $GROQ_EXISTS)"
        else
            if curl -sf -b "$ONEAPI_COOKIE" -X POST "http://127.0.0.1:3001/api/channel/" \
                -H "Content-Type: application/json" \
                -d "{\"type\":1,\"name\":\"Groq\",\"models\":\"llama-3.1-8b-instant,deepseek-r1,deepseek/deepseek-r1\",\"model_mapping\":\"{\\\"deepseek-r1\\\":\\\"llama-3.1-8b-instant\\\",\\\"deepseek/deepseek-r1\\\":\\\"llama-3.1-8b-instant\\\",\\\"default\\\":\\\"llama-3.1-8b-instant\\\"}\",\"base_url\":\"https://api.groq.com/openai\",\"key\":\"$GROQ_API_KEY\",\"group\":\"default\"}" \
                > /dev/null 2>&1; then
                echo "[entrypoint] Groq channel created"
            else
                echo "[entrypoint] Groq channel creation failed"
            fi
        fi
        rm -f "$ONEAPI_COOKIE"
    else
        echo "[entrypoint] One API admin login failed (password may have changed), skipping Groq setup"
    fi
else
    echo "[entrypoint] GROQ_API_KEY not set, skipping Groq setup"
fi

echo "[entrypoint] Starting gateway..."
if [ -n "$LAUNCHER_COOKIE" ]; then
    for i in $(seq 1 10); do
        if curl -sf -b "$LAUNCHER_COOKIE" -X POST http://127.0.0.1:18800/api/gateway/start \
            -H "Content-Type: application/json" \
            -d '{}' > /dev/null 2>&1; then
            echo "[entrypoint] Gateway started"
            break
        fi
        if [ "$i" -eq 10 ]; then
            echo "[entrypoint] WARNING: Could not start gateway"
        fi
        sleep 2
    done
fi

echo "[entrypoint] All services running"
wait "$SUPERVISOR_PID"
