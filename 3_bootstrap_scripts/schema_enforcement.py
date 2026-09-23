#!/usr/bin/env python3
# Minimal stub: ensure feature_flags.yml and plan file exist; extend with jsonschema as needed.
import sys, os, pathlib
missing=[]
for p in ["0_phase0_bootstrap/feature_flags.yml","6_ai_runtime_context/ACTIVE_PLAN.yaml"]:
    if not pathlib.Path(p).exists(): missing.append(p)
if missing:
    print("[schema] missing:", ", ".join(missing)); sys.exit(1)
print("[schema] OK")

