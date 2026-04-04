#!/bin/bash
# truncation-check.sh
# Runs after Grep and Bash tool calls.
# Detects when tool output was truncated (>50K chars -> 2KB preview).
# Warns the agent to read the full file or narrow scope.

INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')

TOOL_RESPONSE=$(echo "$INPUT" | jq -r '
  if (.tool_response | type) == "string" then .tool_response
  elif (.tool_response | type) == "object" then (.tool_response | tostring)
  else empty
  end
')

if echo "$TOOL_RESPONSE" | grep -q "Output too large"; then
  echo "{\"additionalContext\": \"WARNING: Tool output was truncated to a 2KB preview. The full output was saved to disk. Read the full file at the given path before acting on these results, or re-run with narrower scope (single directory, stricter pattern).\"}"
  exit 0
fi

if [ "$TOOL_NAME" = "Grep" ]; then
  RESULT_COUNT=$(echo "$TOOL_RESPONSE" | grep -c "^" 2>/dev/null || echo "0")
  PATTERN=$(echo "$INPUT" | jq -r '.tool_input.pattern // empty')

  if [ "$RESULT_COUNT" -lt 5 ] && [ -n "$PATTERN" ]; then
    echo "{\"additionalContext\": \"Low result count (${RESULT_COUNT}) for pattern '${PATTERN}'. If this seems too few, results may have been truncated. Consider re-running with narrower directory scope.\"}"
    exit 0
  fi
fi

exit 0
