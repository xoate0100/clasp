#!/usr/bin/env bash
set -euo pipefail
CHANGED=$(git diff --cached --name-only)
[ -z "$CHANGED" ] && exit 0
# Basic sanity for yaml/json/toml/xml already covered by pre-commit-hooks.
# Add repo-level checks if needed.
exit 0

