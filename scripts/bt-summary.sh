#!/usr/bin/env bash
# Quick summary of a backtest's outputs, printed to terminal.
# Usage: scripts/bt-summary.sh [strategy_output_dir]
# Default: wtpy/demos/cta_stk_bt/outputs_bt/pydt_SH510300
set -euo pipefail

cd "$(dirname "$0")/.."

DIR="${1:-wtpy/demos/cta_stk_bt/outputs_bt/pydt_SH510300}"

if [[ ! -d "$DIR" ]]; then
  echo "Directory not found: $DIR" >&2
  exit 1
fi

echo "=== Backtest summary: $DIR ==="
echo
echo "-- Files --"
ls -lh "$DIR"
echo
echo "-- trades.csv (first 5 + last 5) --"
head -6 "$DIR/trades.csv"
echo "..."
tail -5 "$DIR/trades.csv"
echo
echo "-- funds.csv (last 10 days) --"
head -1 "$DIR/funds.csv"
tail -10 "$DIR/funds.csv"
echo
echo "-- closes.csv row count --"
CLOSE_ROWS=$(($(wc -l < "$DIR/closes.csv") - 1))
TRADE_ROWS=$(($(wc -l < "$DIR/trades.csv") - 1))
FUND_ROWS=$(($(wc -l < "$DIR/funds.csv") - 1))
echo "trades: $TRADE_ROWS | closes: $CLOSE_ROWS | fund days: $FUND_ROWS"
echo
echo "For PnL Excel report, look in:"
PARENT_DIR=$(dirname "$(dirname "$DIR")")
find "$PARENT_DIR" -maxdepth 1 -name "*.xlsx" 2>/dev/null
