#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

if [[ ! -x .venv/bin/python ]]; then
    echo "Create .venv and install .[dev] before running scripts/check.sh" >&2
    exit 1
fi

.venv/bin/ruff format --check src tests scripts
.venv/bin/ruff check src tests scripts
bash scripts/run-pyright.sh
.venv/bin/python scripts/check_docs.py
.venv/bin/python -m pytest -q \
    --cov=ff \
    --cov=esim \
    --cov-branch \
    --cov-report=term-missing \
    --cov-fail-under=90
.venv/bin/python -m pip check
