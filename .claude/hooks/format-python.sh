#!/bin/bash
# format-python.sh
# PostToolUse hook: auto-format Python files via `uv run ruff format`.
# Runs after Write/Edit/MultiEdit on .py files inside $CLAUDE_PROJECT_DIR.
# Best-effort: never blocks the agent.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')

[[ -z $FILE_PATH ]] && exit 0
[[ "$FILE_PATH" != *.py ]] && exit 0
[[ "$FILE_PATH" != "$CLAUDE_PROJECT_DIR"/* ]] && exit 0

case "$FILE_PATH" in
  */.venv/*|*/.tox/*|*/build/*|*/dist/*|*/__pycache__/*|*/node_modules/*|*/.ruff_cache/*) exit 0 ;;
esac

cd "$CLAUDE_PROJECT_DIR" && uv run ruff format "$FILE_PATH" >/dev/null 2>&1 || true
exit 0
