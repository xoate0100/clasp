#!/usr/bin/env bash
set -euo pipefail
STATUS=0
# Secrets scan (basic): grep common patterns; replace with gitleaks if available.
if git grep -nE "(AWS_SECRET|BEGIN RSA PRIVATE KEY|password\s*=|api_key\s*=)" -- . ':!*.md' ':!3_bootstrap_scripts/security_scan.sh' ; then
  echo "Secret-like patterns found."
  STATUS=1
fi
# Node audit (best-effort)
if [ -f "frontend/package.json" ]; then
  (cd frontend && npm audit --audit-level=high || true)
fi
exit $STATUS
