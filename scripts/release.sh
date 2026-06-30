#!/usr/bin/env bash
set -euo pipefail

cz bump --changelog --check-consistency

VERSION=$(grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')

# Delete the local tag created by cz bump so CI creates it on main.
# If the tag is missing (e.g. wrong format), proceed without failing.
git tag -d "v${VERSION}" || true

# cz bump rewrites pyproject.toml's version but leaves uv.lock's resenhazord2-core
# entry stale, so every later `uv` run would rewrite the lock and trip the hooks.
# Refresh it and fold it into the bump commit (still local — not pushed yet).
uv lock
git add uv.lock
git commit --amend --no-edit

echo "Bumped to v${VERSION}. Local tag deleted — CI will create it on main."
