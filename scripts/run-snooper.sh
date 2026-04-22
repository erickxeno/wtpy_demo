#!/usr/bin/env bash
# Launch WtBtSnooper (backtest web UI) in the container on port 8081.
# After it prints "Starting on 0.0.0.0:8081", open this URL on macOS:
#   http://127.0.0.1:8081/backtest/backtest.html
#
# Usage:
#   scripts/run-snooper.sh           # foreground (Ctrl+C to stop)
#   scripts/run-snooper.sh --detach  # background
set -euo pipefail

cd "$(dirname "$0")/.."

DETACH="${1:-}"

if ! docker compose ps --services --filter status=running | grep -q '^wtpy$'; then
  docker compose up -d
fi

# Kill any stale snooper process first (idempotent)
docker compose exec -T wtpy bash -c "pkill -f 'launch_snooper.py' 2>/dev/null || true"
sleep 1

if [[ "$DETACH" == "--detach" || "$DETACH" == "-d" ]]; then
  docker exec -d wtpy-dev bash -c "nohup python /workspace/docker/launch_snooper.py > /tmp/snooper.log 2>&1 &"
  sleep 2
  echo "[snooper] Running in background."
  echo "[snooper] Log: docker exec wtpy-dev tail -f /tmp/snooper.log"
  echo "[snooper] URL: http://127.0.0.1:8081/backtest/backtest.html"
else
  docker compose exec wtpy python /workspace/docker/launch_snooper.py
fi
