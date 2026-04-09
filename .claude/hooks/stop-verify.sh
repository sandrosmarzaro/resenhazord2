#!/bin/bash
# stop-verify.sh
# Runs when Claude tries to complete a task (Stop event).
# Blocks "Done!" until the project lints and type-checks pass.
# Infinite-loop protection: stop_hook_active=true lets a retry through.

INPUT=$(cat)

STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
if [ "$STOP_ACTIVE" = "true" ]; then
  exit 0
fi

ERRORS=""
CHECKS_RUN=0

# --- Gateway (TypeScript) ---
GATEWAY_DIR="$CLAUDE_PROJECT_DIR/gateway"
if [ -f "$GATEWAY_DIR/tsconfig.json" ]; then
  CHECKS_RUN=$((CHECKS_RUN + 1))
  TSC_OUTPUT=$(cd "$GATEWAY_DIR" && bun typecheck 2>&1)
  if [ $? -ne 0 ]; then
    ERRORS="${ERRORS}TS TYPE CHECK FAILED:\n$(echo "$TSC_OUTPUT" | head -30)\n\n"
  fi
fi

if [ -f "$GATEWAY_DIR/eslint.config.mjs" ] || [ -f "$GATEWAY_DIR/eslint.config.js" ] || [ -f "$GATEWAY_DIR/eslint.config.ts" ] || [ -f "$GATEWAY_DIR/.eslintrc.json" ]; then
  CHECKS_RUN=$((CHECKS_RUN + 1))
  LINT_OUTPUT=$(cd "$GATEWAY_DIR" && bun lint 2>&1)
  if [ $? -ne 0 ]; then
    ERRORS="${ERRORS}TS LINT FAILED:\n$(echo "$LINT_OUTPUT" | head -30)\n\n"
  fi
fi

# --- Python (root) ---
if [ -f "$CLAUDE_PROJECT_DIR/pyproject.toml" ]; then
  CHECKS_RUN=$((CHECKS_RUN + 1))
  RUFF_OUTPUT=$(cd "$CLAUDE_PROJECT_DIR" && uv run ruff check . 2>&1)
  if [ $? -ne 0 ]; then
    ERRORS="${ERRORS}RUFF FAILED:\n$(echo "$RUFF_OUTPUT" | head -30)\n\n"
  fi

  CHECKS_RUN=$((CHECKS_RUN + 1))
  PYRIGHT_OUTPUT=$(cd "$CLAUDE_PROJECT_DIR" && uv run basedpyright 2>&1)
  if [ $? -ne 0 ]; then
    ERRORS="${ERRORS}BASEDPYRIGHT FAILED:\n$(echo "$PYRIGHT_OUTPUT" | head -30)\n\n"
  fi
fi


# --- Report ---
if [ -n "$ERRORS" ]; then
  SUMMARY="Verification failed ($CHECKS_RUN checks ran). Fix these errors before completing:\n\n${ERRORS}"
  echo "{\"decision\": \"block\", \"reason\": \"${SUMMARY}\"}"
  exit 2
fi

if [ $CHECKS_RUN -eq 0 ]; then
  echo "{\"additionalContext\": \"No type-checker, linter, or test suite detected. Task completion is unverified. State this to the user.\"}"
fi

exit 0
