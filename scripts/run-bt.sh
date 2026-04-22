#!/usr/bin/env bash
# Run a wtpy backtest demo inside the container, then post-process to
# generate summary.json (required by WtBtSnooper's analysis endpoints).
#
# Usage: scripts/run-bt.sh [demo_dir] [capital]
#   demo_dir  relative path under wtpy/, default: demos/cta_stk_bt
#   capital   initial capital used when generating summary.json, default: 5000
set -euo pipefail

cd "$(dirname "$0")/.."

DEMO_DIR="${1:-demos/cta_stk_bt}"
CAPITAL="${2:-5000}"

# Paths starting with "bt/" are our custom backtests (mounted at /workspace/bt),
# everything else resolves under wtpy's demos tree (/workspace/wtpy).
if [[ "$DEMO_DIR" == bt/* ]]; then
  CONTAINER_DIR="/workspace/${DEMO_DIR}"
else
  CONTAINER_DIR="/workspace/wtpy/${DEMO_DIR}"
fi

if ! docker compose ps --services --filter status=running | grep -q '^wtpy$'; then
  docker compose up -d
fi

echo "[run-bt] Running backtest in ${DEMO_DIR} (${CONTAINER_DIR}) ..."
echo "" | docker compose exec -T -w "${CONTAINER_DIR}" wtpy python runBT.py

OUTPUTS_BT="${CONTAINER_DIR}/outputs_bt"
echo
echo "[run-bt] Post-processing outputs in ${OUTPUTS_BT} with capital=${CAPITAL} ..."
docker compose exec -T wtpy bash -c "
set -e
for d in ${OUTPUTS_BT}/*/; do
  [ -d \"\$d\" ] || continue
  straid=\$(basename \"\$d\")
  python /workspace/docker/gen_summary.py ${OUTPUTS_BT} \"\$straid\" ${CAPITAL}
done
"

echo
echo "[run-bt] Done. View results in WtBtSnooper:"
echo "         http://127.0.0.1:8081/backtest/backtest.html"
echo "         (run ./scripts/run-snooper.sh if not started yet)"
