#!/usr/bin/env bash
# Neutral meta-framework dispatcher (POSIX).
# Parses adapters/<id>/stack_adapter.json without requiring Python when Node is
# available (required for the node adapter falsifiability path).
# Verb dispatch uses governance_runtime (DEC-0005); product_stack is informational.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

verb="${1:-help}"
shift || true

if [[ "$verb" == "help" || "$verb" == "-h" || "$verb" == "--help" ]]; then
  cat <<'EOF'
meta.sh — stack-agnostic meta-framework dispatcher

Usage:  ./meta.sh <verb> [args...]

Required verbs:
  init, generate-context, validate, check-updates, apply-updates,
  submit-feedback, health, crosswalk

Active adapter: 0_phase0_bootstrap/stack_adapter.yaml
(missing selection → adapters/generic)
EOF
  exit 0
fi

active_file="0_phase0_bootstrap/stack_adapter.yaml"
adapter_id="generic"
if [[ -f "$active_file" ]]; then
  adapter_id="$(grep -E '^\s*adapter:' "$active_file" | head -1 | sed -E 's/.*adapter:[[:space:]]*["'\'']?([a-zA-Z0-9_-]+).*/\1/')"
  adapter_id="${adapter_id:-generic}"
  if [[ ! -f "adapters/${adapter_id}/stack_adapter.json" ]]; then
    echo "[meta] adapter='$adapter_id' missing; falling back to generic" >&2
    adapter_id="generic"
  fi
fi

manifest="adapters/${adapter_id}/stack_adapter.json"
if [[ ! -f "$manifest" ]]; then
  echo "[meta] Adapter manifest not found: $manifest" >&2
  exit 2
fi

# DEC-0005: verb dispatch consults governance_runtime only — never product_stack.
json_get_governance_runtime() {
  local man="$1"
  if command -v node >/dev/null 2>&1; then
    node -e "
const m=JSON.parse(require('fs').readFileSync(process.argv[1],'utf8'));
process.stdout.write(m.governance_runtime||'');
" "$man"
    return $?
  fi
  if command -v python >/dev/null 2>&1; then
    python -c "import json,sys; m=json.load(open(sys.argv[1],encoding='utf-8')); print(m.get('governance_runtime') or '', end='')" "$man"
    return $?
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import json,sys; m=json.load(open(sys.argv[1],encoding='utf-8')); print(m.get('governance_runtime') or '', end='')" "$man"
    return $?
  fi
  return 3
}

dispatch_runtime="$(json_get_governance_runtime "$manifest" 2>/dev/null || true)"
dispatch_runtime="${dispatch_runtime:-$adapter_id}"
if [[ "$dispatch_runtime" != "$adapter_id" ]]; then
  echo "[meta] governance_runtime='$dispatch_runtime' does not match selected adapter='$adapter_id'" >&2
  exit 2
fi

json_get_run() {
  local man="$1" v="$2"
  if command -v node >/dev/null 2>&1; then
    node -e "
const fs=require('fs');
const m=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));
let v=process.argv[2];
v=(m.aliases&&m.aliases[v])||v;
const c=(m.commands&&m.commands[v])||{};
if(!c.run) process.exit(2);
process.stdout.write(c.run);
" "$man" "$v"
    return $?
  fi
  if command -v python >/dev/null 2>&1; then
    python -c "
import json,sys
m=json.load(open(sys.argv[1],encoding='utf-8'))
v=sys.argv[2]
v=(m.get('aliases') or {}).get(v,v)
c=(m.get('commands') or {}).get(v) or {}
assert c.get('run')
print(c['run'])
" "$man" "$v"
    return $?
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import json,sys
m=json.load(open(sys.argv[1],encoding='utf-8'))
v=sys.argv[2]
v=(m.get('aliases') or {}).get(v,v)
c=(m.get('commands') or {}).get(v) or {}
assert c.get('run')
print(c['run'])
" "$man" "$v"
    return $?
  fi
  echo "[meta] Need node or python to parse adapter JSON" >&2
  return 3
}

# Prefer node parser when adapter is node (no Python on PATH allowed)
if [[ "$adapter_id" == "node" ]]; then
  if ! command -v node >/dev/null 2>&1; then
    echo "[meta] node adapter requires node on PATH" >&2
    exit 3
  fi
fi

run="$(json_get_run "$manifest" "$verb")" || {
  echo "[meta] Unknown verb '$verb' for adapter '$adapter_id'" >&2
  exit 2
}

echo "[meta] adapter=$adapter_id governance_runtime=$dispatch_runtime verb=$verb"
echo "[meta] exec: $run $*"
# shellcheck disable=SC2086
exec $run "$@"
