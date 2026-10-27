#!/usr/bin/env bash
set -euo pipefail
case "$MODE" in
  check | plan | gate) ;;
  *) echo "::error::mode is check, plan or gate, not $MODE"; exit 1 ;;
esac
if [ "$MODE" = gate ] && { [ -z "${POLICY:-}" ] || [ -z "${TARGET:-}" ]; }; then
  echo '::error::gate requires policy and target inputs'
  exit 2
fi
uv sync --project "$ACTION_PATH" --locked --no-dev --quiet
