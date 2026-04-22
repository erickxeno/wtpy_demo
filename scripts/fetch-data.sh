#!/usr/bin/env bash
# Fetch ETF/stock bar data via AKShare (runs on host macOS, not in container).
# Output: ./bt/storage/csv/<CODE>_<PERIOD>.csv in wtpy-compatible format.
#
# Usage:
#   scripts/fetch-data.sh                    # default: 510300 5min qfq
#   scripts/fetch-data.sh --symbol 510300 --period 60 --adjust qfq
set -euo pipefail

cd "$(dirname "$0")/.."

VENV_PY=".venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "Missing $VENV_PY. Did you create the host venv?" >&2
  exit 1
fi

"$VENV_PY" scripts/fetch_akshare.py "$@"
