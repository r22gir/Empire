#!/usr/bin/env bash
# Queueing check for the Max chat hook (2026-10-08). No browser, no server, no data.
#   NODE_MODULES=/path/to/empire-command-center/node_modules scripts/check-chat-queue.sh
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
NM=${NODE_MODULES:-$ROOT/node_modules}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
cat > "$OUT/tsconfig.json" <<JSON
{ "compilerOptions": { "outDir": "$OUT/js", "rootDir": "$ROOT/app", "module": "commonjs", "target": "es2020",
  "moduleResolution": "node", "esModuleInterop": true, "skipLibCheck": true, "strict": false, "lib": ["es2020", "dom"],
  "typeRoots": ["$NM/@types"], "types": ["node"], "baseUrl": "$ROOT", "paths": { "react": ["$NM/@types/react/index.d.ts"] } },
  "files": ["$ROOT/app/hooks/__checks__/useChatQueue.check.ts"] }
JSON
"$NM/.bin/tsc" -p "$OUT/tsconfig.json"
mkdir -p "$OUT/js/node_modules/react"
cp "$ROOT/app/hooks/__checks__/react-shim.js" "$OUT/js/node_modules/react/index.js"
node "$OUT/js/hooks/__checks__/useChatQueue.check.js"
