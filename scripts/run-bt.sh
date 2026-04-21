#!/usr/bin/env bash
# Run a wtpy backtest demo inside the container.
# Usage: scripts/run-bt.sh [demo_dir]   # defaults to demos/cta_stk_bt
set -euo pipefail

cd "$(dirname "$0")/.."

DEMO_DIR="${1:-demos/cta_stk_bt}"

if ! docker compose ps --services --filter status=running | grep -q '^wtpy$'; then
  docker compose up -d
fi

docker compose exec -w "/workspace/wtpy/${DEMO_DIR}" wtpy python runBT.py
