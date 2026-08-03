#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
output="${1:-$project_root/dist/wheelhouse}"
python_command="${FF_PYTHON:-python3}"
onelog_commit="7738cac48b383624b9b5a6bf3434a2a40210c568"

mkdir -p "$output"
if [[ -n "$(find "$output" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    echo "wheelhouse output must be empty: $output" >&2
    exit 2
fi

temporary_directory="$(mktemp -d)"
trap 'rm -rf -- "$temporary_directory"' EXIT

"$python_command" -m pip wheel \
    "git+https://github.com/BottiCelle/onelog.git@$onelog_commit" \
    --wheel-dir "$output"
"$python_command" -m pip wheel "$project_root" \
    --no-deps \
    --wheel-dir "$output"

"$python_command" -m venv "$temporary_directory/smoke"
"$temporary_directory/smoke/bin/python" -m pip install \
    --no-index \
    --find-links "$output" \
    esim==0.2.0
"$temporary_directory/smoke/bin/python" -m pip check
"$temporary_directory/smoke/bin/ff" --help >/dev/null

(
    cd "$output"
    sha256sum ./*.whl >SHA256SUMS
)
