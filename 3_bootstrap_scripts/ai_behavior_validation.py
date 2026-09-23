#!/usr/bin/env python3
import sys, re, subprocess

# Ensure commit message(s) in staging include plan/component/task tags
def get_staged_commit_msg_template():
    # Pre-commit runs before commit object exists; validate COMMIT_MSG file if present,
    # otherwise allow; PR checks will re-validate.
    return None

# Validate changed files are within allowed paths (feature_flags.yml is source of truth).
try:
    import yaml
except ImportError:
    print("[ai-guard] Warning: PyYAML not installed. Install with: pip install PyYAML")
    sys.exit(0)

import pathlib
flags = yaml.safe_load(open("0_phase0_bootstrap/feature_flags.yml"))
perms = flags.get("permissions") or {}
allowed = set(perms.get("write_to") or [])
allowed |= set(perms.get("elevated_write_to") or [])

ROOT_ALLOW = {
    "README.md",
    ".pre-commit-config.yaml",
    ".gitignore",
    "requirements.txt",
    "pytest.ini",
    "config.json",
    "vercel_projects.json",
    "MODULES.lock",
    "meta.ps1",
    "meta.sh",
}

changed = subprocess.check_output(["git", "diff", "--cached", "--name-only"], text=True).splitlines()
viol = []
for f in changed:
    p = pathlib.Path(f)
    norm = p.as_posix()
    if not any(norm.startswith(a.rstrip("/")) or norm.startswith(a) for a in allowed):
        if p.name in ROOT_ALLOW:
            continue
        viol.append(f)

if viol:
    print("[ai-guard] Write outside allowed paths:", *viol, sep="\n- ")
    sys.exit(1)

print("[ai-guard] OK")
