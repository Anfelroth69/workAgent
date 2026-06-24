#!/bin/sh
set -e

echo "[picoclaw] Waiting for One API to be healthy..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:3000/api/status > /dev/null 2>&1; then
    echo "[picoclaw] One API is healthy, starting Pico Claw..."
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "[picoclaw] ERROR: One API not available after 60s"
    exit 1
  fi
  sleep 2
done

exec picoclaw gateway
