#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"

if command -v npm >/dev/null 2>&1; then
    npm --prefix tools/typecheck run typecheck --silent
elif [[ -x .tools/node/bin/node ]]; then
    .tools/node/bin/node tools/typecheck/node_modules/pyright/index.js --project tools/typecheck/pyrightconfig.json
    .tools/node/bin/node tools/typecheck/node_modules/pyright/index.js --project tools/typecheck/pyrightconfig.tests.json
else
    echo "Node 24 and npm are required for Pyright" >&2
    exit 1
fi
