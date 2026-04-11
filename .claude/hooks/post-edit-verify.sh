#!/bin/bash
# post-edit-verify.sh
# Runs after every Write/Edit/MultiEdit.
# Blocks the agent from proceeding if lint fails on the modified file.
# Type-checking runs only at Stop (via stop-verify.sh) to avoid slow delays.

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

if ! echo "$FILE_PATH" | grep -qE '\.(ts|tsx|js|jsx|py)$'; then
  exit 0
fi

ERRORS=""

# --- TypeScript / JavaScript (gateway/) ---
if echo "$FILE_PATH" | grep -qE '\.(ts|tsx|js|jsx)$'; then
  GATEWAY_DIR="$CLAUDE_PROJECT_DIR/gateway"
  if [ -f "$GATEWAY_DIR/eslint.config.mjs" ] || [ -f "$GATEWAY_DIR/eslint.config.js" ] || [ -f "$GATEWAY_DIR/eslint.config.ts" ] || [ -f "$GATEWAY_DIR/.eslintrc" ] || [ -f "$GATEWAY_DIR/.eslintrc.json" ]; then
    ESLINT_OUTPUT=$(cd "$GATEWAY_DIR" && npx eslint --quiet "$FILE_PATH" 2>&1)
    if [ $? -ne 0 ]; then
      ERRORS="${ERRORS}eslint errors in ${FILE_PATH}:\n${ESLINT_OUTPUT}\n\n"
    fi
  fi
  if [ -f "$GATEWAY_DIR/package.json" ] && grep -q '"prettier"' "$GATEWAY_DIR/package.json"; then
    PRETTIER_OUTPUT=$(cd "$GATEWAY_DIR" && bun prettier --check "$FILE_PATH" 2>&1)
    if [ $? -ne 0 ]; then
      ERRORS="${ERRORS}prettier errors in ${FILE_PATH}:\n${PRETTIER_OUTPUT}\n\n"
    fi
  fi
fi

# --- Python (root) ---
# Uses uv run ruff (project-managed tooling, not system ruff)
if echo "$FILE_PATH" | grep -qE '\.py$'; then
  RUFF_OUTPUT=$(cd "$CLAUDE_PROJECT_DIR" && uv run ruff check "$FILE_PATH" 2>&1)
  if [ $? -ne 0 ]; then
    ERRORS="${ERRORS}ruff errors in ${FILE_PATH}:\n${RUFF_OUTPUT}\n\n"
  fi
  RUFF_FORMAT_OUTPUT=$(cd "$CLAUDE_PROJECT_DIR" && uv run ruff format --check "$FILE_PATH" 2>&1)
  if [ $? -ne 0 ]; then
    ERRORS="${ERRORS}ruff format errors in ${FILE_PATH}:\n${RUFF_FORMAT_OUTPUT}\n\n"
  fi
fi

if [ -n "$ERRORS" ]; then
  TRUNCATED=$(echo -e "$ERRORS" | head -50)
  echo "{\"decision\": \"block\", \"reason\": \"Lint failed. Fix before continuing:\n${TRUNCATED}\"}"
  exit 2
fi

exit 0
