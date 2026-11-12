#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
gate="${1:-all}"
mkdir -p "$root_dir/artifacts/quality"

write_summary() {
  exit_code=$?
  if [[ "$exit_code" -eq 0 ]]; then status=success; else status=error; fi
  cat > "$root_dir/artifacts/quality/${gate}-summary.json" <<EOF
{"status":"$status","summary":"Gate $gate exited with code $exit_code","next_actions":["Run bash scripts/quality-gates.sh $gate and inspect the first failing command"],"artifacts":["artifacts/quality/backend.xml","artifacts/quality/coverage.xml","artifacts/quality/ai-eval.json"]}
EOF
}
trap write_summary EXIT

backend_static() {
  cd "$root_dir/backend"
  uv run --extra dev ruff check .
  uv run --extra dev ruff format --check .
  uv run --extra dev mypy --strict src
  uv run --extra dev lint-imports
}

backend_tests() {
  cd "$root_dir/backend"
  uv run --extra dev pytest -q \
    --cov=src.account.domain.services.hybrid_availability_rule_engine \
    --cov=src.execution.public_api \
    --cov=src.planning.domain.services.spatio_temporal_engine \
    --cov-branch --cov-report=term --cov-report="xml:$root_dir/artifacts/quality/coverage.xml" \
    --junitxml="$root_dir/artifacts/quality/backend.xml"
  uv run --extra dev python -m tests.ai_evals.constraints_eval > "$root_dir/artifacts/quality/ai-eval.json"
}

frontend_static() {
  cd "$root_dir/frontend"
  pnpm exec ng lint
  pnpm exec ng test --watch=false
  pnpm exec ng build --configuration production
}

frontend_e2e() {
  cd "$root_dir/frontend"
  pnpm exec playwright test
}

case "$gate" in
  backend-static) backend_static ;;
  backend-tests) backend_tests ;;
  frontend-static) frontend_static ;;
  frontend-e2e) frontend_e2e ;;
  all) backend_static; backend_tests; frontend_static; frontend_e2e ;;
  *) echo "Unknown gate: $gate" >&2; exit 2 ;;
esac
