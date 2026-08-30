#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"

if [[ ! -x .venv/bin/python ]]; then
    echo "Create .venv and install .[dev] before running tools/quality/check.sh" >&2
    exit 1
fi

.venv/bin/ruff format --check src tests tools
.venv/bin/ruff check src tests tools
bash tools/quality/run-pyright.sh
.venv/bin/python tools/docs/generate_user_guides.py --check
.venv/bin/python tools/quality/check_docs.py
.venv/bin/python -m pytest -q \
    --cov=ff \
    --cov=esim \
    --cov-branch \
    --cov-report=term-missing \
    --cov-fail-under=90
.venv/bin/python -m pip check
