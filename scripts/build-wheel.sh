#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
output="${1:-$project_root/dist}"
python_command="${FF_PYTHON:-python3}"

mkdir -p "$output"
output="$(cd -- "$output" && pwd)"

temporary_directory="$(mktemp -d)"
trap 'rm -rf -- "$temporary_directory"' EXIT

source_copy="$temporary_directory/source"
mkdir -p "$source_copy"
cp "$project_root/pyproject.toml" "$project_root/README.md" "$source_copy/"
cp -R "$project_root/src" "$source_copy/src"
find "$source_copy" -type d \( -name __pycache__ -o -name '*.egg-info' \) \
    -prune -exec rm -rf -- {} +

"$python_command" -m pip wheel "$source_copy" \
    --no-build-isolation \
    --no-deps \
    --wheel-dir "$output"
