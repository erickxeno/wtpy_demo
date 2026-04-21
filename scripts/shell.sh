#!/usr/bin/env bash
# Enter an interactive bash shell inside the wtpy dev container.
# If the container is not running, start it first.
set -euo pipefail

cd "$(dirname "$0")/.."

if ! docker compose ps --services --filter status=running | grep -q '^wtpy$'; then
  docker compose up -d
fi

docker compose exec wtpy bash
