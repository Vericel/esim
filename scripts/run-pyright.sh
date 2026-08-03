#!/usr/bin/env bash
set -euo pipefail

if command -v npm >/dev/null 2>&1; then
    npm run typecheck --silent
elif [[ -x .tools/node/bin/node ]]; then
    .tools/node/bin/node node_modules/pyright/index.js --project pyrightconfig.json
    .tools/node/bin/node node_modules/pyright/index.js --project pyrightconfig.tests.json
else
    echo "Node 24 and npm are required for Pyright" >&2
    exit 1
fi
