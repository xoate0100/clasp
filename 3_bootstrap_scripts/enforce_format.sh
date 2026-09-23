#!/usr/bin/env bash
set -euo pipefail
# Frontend: prettier (if package.json exists)
if [ -f "frontend/package.json" ]; then
  npx --yes prettier -w frontend || true
fi
# Backend: black + isort (if pyproject/requirements)
if [ -d "backend" ]; then
  python3 -m pip install --quiet black isort || true
  black backend || true
  isort backend || true
fi
# Shared: try prettier or leave as-is
if [ -f "shared/package.json" ]; then
  npx --yes prettier -w shared || true
fi
# re-add changes
git add -A
exit 0

