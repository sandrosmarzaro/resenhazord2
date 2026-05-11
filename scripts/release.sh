#!/usr/bin/env bash
set -euo pipefail

cz bump --changelog --check-consistency

VERSION=$(grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')

git tag -d "v${VERSION}"

echo "Bumped to v${VERSION}. Local tag deleted — CI will create it on main."
