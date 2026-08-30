#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
output="${1:-$project_root/dist/wheelhouse}"
python_command="${FF_PYTHON:-python3}"
onelog_commit="d60dc49701944d88c90f3bd7fabf5bbbdb7d6f8c"

mkdir -p "$output"
if [[ -n "$(find "$output" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    echo "wheelhouse output must be empty: $output" >&2
    exit 2
fi

temporary_directory="$(mktemp -d)"
trap 'rm -rf -- "$temporary_directory"' EXIT

"$python_command" -m pip wheel \
    "git+https://github.com/BottiCelle/onelog.git@$onelog_commit" \
    "PyYAML>=6.0,<7" \
    --no-build-isolation \
    --wheel-dir "$output"
FF_PYTHON="$python_command" bash "$project_root/scripts/build-wheel.sh" "$output"

"$python_command" -m venv "$temporary_directory/smoke"
"$temporary_directory/smoke/bin/python" -m pip install \
    --no-index \
    --find-links "$output" \
    esim==0.2.0
"$temporary_directory/smoke/bin/python" -m pip check
"$temporary_directory/smoke/bin/ff" --help >/dev/null
"$temporary_directory/smoke/bin/esim" --help >/dev/null

(
    cd "$output"
    sha256sum ./*.whl >SHA256SUMS
)
