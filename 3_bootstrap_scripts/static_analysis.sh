#!/usr/bin/env bash
set -euo pipefail
STATUS=0
if [ -d "backend" ] && find backend -name '*.py' 2>/dev/null | grep -q .; then
  python3 -m pip install --quiet flake8 mypy || true
  flake8 backend || STATUS=1
  mypy backend || STATUS=1
fi
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
  (cd frontend && npm ci --silent && npm run -s typecheck || npm run -s build --if-present) || STATUS=1
fi
exit $STATUS
