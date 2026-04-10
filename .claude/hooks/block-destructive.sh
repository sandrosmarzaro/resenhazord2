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

# For rm: allow within ~/projects/ or relative paths; block everything else
if echo "$COMMAND_CLEAN" | grep -qE '\brm\b'; then
  DECISION=$(echo "$COMMAND_CLEAN" | python3 -c "
import sys, re, os

cmd = sys.stdin.read()
home = os.environ.get('HOME', '')
projects_base = home.rstrip('/') + '/projects/'

# Find all rm invocations and collect their targets
# Strip flags, collect non-flag arguments
targets = []
for m in re.finditer(r'\brm\b((?:\s+-\S+)*)((?:\s+\S+)+)', cmd):
    for arg in m.group(2).split():
        arg = arg.strip('\"\'')
        targets.append(arg)

for arg in targets:
    expanded = arg.replace('~', home).replace('\$HOME', home)
    # Relative paths are within the current project — allow
    if not expanded.startswith('/'):
        continue
    # Absolute paths under ~/projects/ — allow
    if projects_base and expanded.startswith(projects_base):
        continue
    # Anything else (/, /etc, $HOME directly, ..) — deny
    print('deny')
    sys.exit()

print('allow')
" 2>/dev/null || echo "allow")

  if [ "$DECISION" = "deny" ]; then
    echo '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Blocked rm targeting path outside ~/projects/. If intentional, run manually."}}'
  else
    echo '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}'
  fi
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
