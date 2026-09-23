#!/usr/bin/env python3
"""
Gate compliance check: fail if the working tree / commit appears to execute a
still-blocked NEEDS-ANDY gate action.

Reads NEEDS-ANDY/GATES.yaml. For each item with status=blocked, scans for
heuristic evidence that `blocks:` was performed anyway.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    print("[gates-check] PyYAML required")
    sys.exit(0)

ROOT = pathlib.Path(".").resolve()
GATES = ROOT / "NEEDS-ANDY" / "GATES.yaml"

# Heuristics: gate id → (description, callable returning True if violation)
def _diff_names() -> set[str]:
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            text=True,
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
        return {l.strip().replace("\\", "/") for l in out.splitlines() if l.strip()}
    except Exception:
        try:
            out = subprocess.check_output(
                ["git", "diff", "--name-only", "HEAD"],
                text=True,
                cwd=ROOT,
                stderr=subprocess.DEVNULL,
            )
            return {l.strip().replace("\\", "/") for l in out.splitlines() if l.strip()}
        except Exception:
            return set()


def _tags() -> set[str]:
    try:
        out = subprocess.check_output(["git", "tag", "--list", "v4.0.0"], text=True, cwd=ROOT)
        return {t.strip() for t in out.splitlines() if t.strip()}
    except Exception:
        return set()


def check_na_13(changed):
    # Cross-repo education-platform paths must not appear in this hub PR
    for p in changed:
        if "surewealth-education-platform" in p.lower():
            return f"path mentions education-platform: {p}"
    return None


def check_na_14(changed):
    for p in changed:
        if "surewealth-course-factory" in p.lower():
            return f"path mentions course-factory: {p}"
    return None


def check_na_15(_changed):
    if "v4.0.0" in _tags():
        return "git tag v4.0.0 exists while NA-15 is blocked"
    return None


def check_na_16(changed):
    # Deletion of pre-commit or bootstrap shell scripts
    for p in changed:
        if p in (".pre-commit-config.yaml",) or re.search(r"3_bootstrap_scripts/.+\.sh$", p):
            full = ROOT / p
            if not full.exists():
                return f"deleted while NA-16 blocked: {p}"
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-status", "origin/main...HEAD"],
            text=True,
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0].startswith("D"):
                path = parts[-1].replace("\\", "/")
                if path == ".pre-commit-config.yaml" or (
                    path.startswith("3_bootstrap_scripts/") and path.endswith(".sh")
                ):
                    return f"deleted while NA-16 blocked: {path}"
    except Exception:
        pass
    return None


def check_na_10(changed):
    secret_pat = re.compile(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")
    for p in changed:
        fp = ROOT / p
        if not fp.is_file():
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if secret_pat.search(text):
            return f"inline GitHub token-like secret in {p}"
    return None


CHECKERS = {
    "NA-10": check_na_10,
    "NA-13": check_na_13,
    "NA-14": check_na_14,
    "NA-15": check_na_15,
    "NA-16": check_na_16,
}


def main() -> int:
    if not GATES.exists():
        print("[gates-check] WARN: NEEDS-ANDY/GATES.yaml missing")
        return 0

    data = yaml.safe_load(GATES.read_text(encoding="utf-8")) or {}
    items = data.get("items") or []
    changed = _diff_names()
    failures = []

    for item in items:
        status = item.get("status")
        iid = item.get("id")
        if status == "blocked" and iid in CHECKERS:
            hit = CHECKERS[iid](changed)
            if hit:
                failures.append(f"{iid}: {hit} (blocks: {item.get('blocks')})")

    # Validate schema counts roughly
    answered = sum(1 for i in items if i.get("status") == "answered")
    blocked = sum(1 for i in items if i.get("status") == "blocked")
    meta = data.get("meta") or {}
    if meta.get("answered") != answered or meta.get("blocked") != blocked:
        failures.append(
            f"meta counts mismatch: meta answered={meta.get('answered')} blocked={meta.get('blocked')} "
            f"actual answered={answered} blocked={blocked}"
        )

    if failures:
        print("[gates-check] FAIL — blocked gate action evidence detected:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"[gates-check] OK (answered={answered}, blocked={blocked})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
