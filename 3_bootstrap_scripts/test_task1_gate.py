#!/usr/bin/env python3
"""Test Task 1 completion gate without Unicode issues."""

import pathlib
import subprocess
import sys

import yaml

# Get staged files
result = subprocess.run(
    ["git", "diff", "--cached", "--name-only"],
    capture_output=True,
    text=True,
    encoding="utf-8",
)
staged_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]

print("Staged files:", staged_files)

plan_path = pathlib.Path("6_ai_runtime_context/ACTIVE_PLAN.yaml")
if not plan_path.exists():
    print("SKIP: no ACTIVE_PLAN.yaml — not a hub task-gate context")
    sys.exit(0)

plan = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
tasks = plan.get("tasks") or []
matches = [t for t in tasks if isinstance(t, dict) and t.get("id") == 1]
if not matches:
    print("SKIP: plan has no task id=1 — nothing to gate")
    sys.exit(0)

task1 = matches[0]
expected_outputs = task1.get("outputs") or []

print("Task 1 expected outputs:", expected_outputs)

# Check each staged file
for file_path in staged_files:
    if file_path.startswith("6_ai_runtime_context/"):
        print(f"OK: {file_path} (runtime file, allowed)")
        continue

    if file_path in expected_outputs:
        print(f"OK: {file_path} (in expected outputs)")
    else:
        print(f"FAIL: {file_path} (not in expected outputs)")

# Check if outputs exist
print("\nChecking outputs exist:")
for output in expected_outputs:
    exists = pathlib.Path(output).exists()
    print(f"{'OK' if exists else 'MISSING'}: {output}")
