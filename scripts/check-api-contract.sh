#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
scratch_dir="$(mktemp -d)"
trap 'rm -r "$scratch_dir"' EXIT

(
  cd "$root_dir/backend"
  uv run --extra dev python -c 'import json; from src.main import create_app; print(json.dumps(create_app().openapi()))' > "$scratch_dir/openapi.json"
)
(
  cd "$root_dir/frontend"
  pnpm exec openapi-typescript "$scratch_dir/openapi.json" -o "$scratch_dir/schema.d.ts"
  if ! cmp -s src/app/core/api/schema.d.ts "$scratch_dir/schema.d.ts"; then
    echo "API type drift: regenerate frontend/src/app/core/api/schema.d.ts" >&2
    diff -u src/app/core/api/schema.d.ts "$scratch_dir/schema.d.ts" | head -80 || true
    exit 1
  fi
)
