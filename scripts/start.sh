#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mode="${1:-real}"
if [[ "$mode" == "demo" ]]; then
  export MARYRUSS_DEMO=1
  port="${MARYRUSS_PORT:-8001}"
elif [[ "$mode" == "real" ]]; then
  export MARYRUSS_DEMO=0
  port="${MARYRUSS_PORT:-8000}"
else
  echo 'Uso: bash scripts/start.sh [real|demo]' >&2
  exit 2
fi
exec .venv/bin/python manage.py runserver "${MARYRUSS_BIND:-127.0.0.1}:${port}" --noreload
