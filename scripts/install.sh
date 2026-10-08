#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export MARYRUSS_DEMO=0
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --cache-dir .data/pip-cache -r requirements.txt
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py init_admin
env -u MARYRUSS_DB MARYRUSS_DEMO=1 .venv/bin/python manage.py migrate --noinput
env -u MARYRUSS_DB MARYRUSS_DEMO=1 .venv/bin/python manage.py seed_demo
env -u MARYRUSS_DB MARYRUSS_DEMO=1 .venv/bin/python manage.py seed_planner_demo
.venv/bin/python manage.py check
