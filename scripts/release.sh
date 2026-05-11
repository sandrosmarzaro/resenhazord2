#!/usr/bin/env bash
set -euo pipefail

cz bump --changelog --check-consistency

VERSION=$(grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')

# Delete the local tag created by cz bump so CI creates it on main.
# If the tag is missing (e.g. wrong format), proceed without failing.
git tag -d "v${VERSION}" || true

echo "Bumped to v${VERSION}. Local tag deleted — CI will create it on main."
