#!/usr/bin/env python3
"""
Resurrection scan — keyword/pattern guard against deprecated decision resurrection.

Scans git diff (staged by default), file list, or stdin for resurrection_trigger_keywords
from DECISION_REGISTRY.yaml. Intentionally simple and deterministic (not LLM judgment).

Usage:
    python 3_bootstrap_scripts/resurrection_scan.py
    python 3_bootstrap_scripts/resurrection_scan.py --diff
    python 3_bootstrap_scripts/resurrection_scan.py --files path/to/file.md
    echo "polyrepo split" | python 3_bootstrap_scripts/resurrection_scan.py --stdin
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    import yaml
except ImportError:
    print("[resurrection] ERROR: PyYAML required. pip install PyYAML")
    sys.exit(1)

from agentic.diff_utils import extract_added_lines
from agentic.registry import active_resurrection_keywords, load_decision_registry


def _git_diff(staged: bool = True) -> str:
    cmd = ["git", "diff", "--cached"] if staged else ["git", "diff"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT, check=False)
        return result.stdout or ""
    except FileNotFoundError:
        return ""


def _read_files(paths: list[str]) -> str:
    chunks: list[str] = []
    for rel in paths:
        path = REPO_ROOT / rel
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def scan_text(text: str, registry: dict | None = None) -> list[dict]:
    registry = registry or load_decision_registry(REPO_ROOT)
    hits: list[dict] = []
    lowered = text.lower()

    for decision_id, keyword, status in active_resurrection_keywords(registry):
        if keyword.lower() in lowered:
            hits.append(
                {
                    "decision_id": decision_id,
                    "keyword": keyword,
                    "status": status,
                }
            )
            continue
        try:
            if re.search(keyword, text, re.IGNORECASE):
                hits.append(
                    {
                        "decision_id": decision_id,
                        "keyword": keyword,
                        "status": status,
                    }
                )
        except re.error:
            if keyword.lower() in lowered:
                hits.append(
                    {
                        "decision_id": decision_id,
                        "keyword": keyword,
                        "status": status,
                    }
                )
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan for forbidden decision resurrection keywords")
    parser.add_argument("--diff", action="store_true", help="Scan unstaged git diff")
    parser.add_argument("--staged", action="store_true", default=True, help="Scan staged diff (default)")
    parser.add_argument("--files", nargs="*", default=[], help="Explicit files to scan")
    parser.add_argument("--stdin", action="store_true", help="Read content from stdin")
    parser.add_argument("--text", default="", help="Inline text to scan")
    args = parser.parse_args()

    if args.stdin:
        content = sys.stdin.read()
    elif args.text:
        content = args.text
    elif args.files:
        content = _read_files(args.files)
    else:
        diff = _git_diff(staged=not args.diff)
        content = extract_added_lines(diff) if diff else ""

    if not content.strip():
        print("[resurrection] OK: no content to scan")
        return 0

    hits = scan_text(content)
    if not hits:
        print("[resurrection] OK: no forbidden resurrection keywords detected")
        return 0

    print("[resurrection] FAIL: forbidden resurrection keyword(s) detected:")
    seen = set()
    for hit in hits:
        key = (hit["decision_id"], hit["keyword"])
        if key in seen:
            continue
        seen.add(key)
        print(
            f"  - {hit['decision_id']} ({hit['status']}): matched '{hit['keyword']}'"
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
