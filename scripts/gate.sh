#!/usr/bin/env bash
set -euo pipefail
set -f
report="$RUNNER_TEMP/exacly-gate.txt"
status=0
if [ -z "${MODEL//[[:space:]]/}" ]; then
  echo 'exacly gate: model input must name config/state files, folders or patterns' > "$report"
  status=2
else
  # Match the check/plan input: split spaces/newlines, and let Exacly expand patterns.
  # shellcheck disable=SC2206
  paths=($MODEL)
  models=()
  for path in "${paths[@]}"; do models+=(-m "$path"); done
  uv run --project "$ACTION_PATH" --no-dev --no-sync exacly gate "${models[@]}" \
    --policy="$POLICY" --target="$TARGET" > "$report" 2>&1 || status=$?
fi
cat "$report"
{ echo '### Exacly readiness gate'; echo; echo '```'; cat "$report"; echo '```'; } >> "$GITHUB_STEP_SUMMARY"
exit "$status"
