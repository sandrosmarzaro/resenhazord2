#!/bin/bash
# block-destructive.sh
# PreToolUse hook for Bash commands.
# Blocks obviously destructive operations before they execute.

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$COMMAND" ]; then
  exit 0
fi

# Strip heredoc bodies (content between <<'EOF'/<<EOF and its closing delimiter)
# so patterns in commit messages don't trigger false positives.
COMMAND_CLEAN=$(echo "$COMMAND" | python3 -c "
import sys, re
text = sys.stdin.read()
text = re.sub(r\"(<<['\\\"]?(\\w+)['\\\"]?)(.*?)^\\2\$\", r'\\1', text, flags=re.DOTALL|re.MULTILINE)
print(text, end='')
" 2>/dev/null || echo "$COMMAND")

# Block recursive deletion of root, home, or parent directory
if echo "$COMMAND_CLEAN" | grep -qE 'rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|(-[a-zA-Z]*\s+)*)(\/|~|\$HOME|\.\.)'; then
  echo '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Blocked destructive rm command targeting root, home, or parent directory. If intentional, run manually."}}'
  exit 0
fi

# Block database destruction
if echo "$COMMAND_CLEAN" | grep -qiE 'DROP\s+(TABLE|DATABASE)|TRUNCATE\s+TABLE|DELETE\s+FROM\s+\S+\s*;?\s*$'; then
  echo '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Blocked destructive database command. If intentional, run manually."}}'
  exit 0
fi

# Block force pushes and hard resets to remote
if echo "$COMMAND_CLEAN" | grep -qE 'git\s+push\s+.*--force|git\s+push\s+-f\b|git\s+reset\s+--hard\s+(HEAD~|origin)'; then
  echo '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Blocked force push or hard reset. If intentional, run manually."}}'
  exit 0
fi

# Block .env file reads (prevent accidental credential exposure)
if echo "$COMMAND_CLEAN" | grep -qE '(cat|less|head|tail|more|source|grep|sed|awk|bat)\s+\.env\b'; then
  echo '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Blocked .env file access. Credentials should not be read by the agent."}}'
  exit 0
fi

exit 0
