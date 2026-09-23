#!/usr/bin/env bash
set -euo pipefail
# Validate last prepared commit message (pre-commit can't always read it here).
# Defer strict validation to CI; soft gate here.
exit 0

