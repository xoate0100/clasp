#!/usr/bin/env python3
"""
Drift vector check — scan content for named anti-patterns (DV_* catalog).

Links to DECISION_REGISTRY resurrection keywords where linked_decision is set.
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
    print("[drift-vector] ERROR: PyYAML required")
    sys.exit(1)

from agentic.diff_utils import extract_added_lines, is_guardrail_catalog_path
from agentic.registry import active_resurrection_keywords, load_decision_registry, load_drift_vectors


def _git_diff(staged: bool = True) -> str:
    cmd = ["git", "diff", "--cached"] if staged else ["git", "diff"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT, check=False)
        return result.stdout or ""
    except FileNotFoundError:
        return ""


def _staged_paths() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )
        return [p.strip().replace("\\", "/") for p in (result.stdout or "").splitlines() if p.strip()]
    except FileNotFoundError:
        return []


def scan(text: str, staged_paths: list[str] | None = None) -> list[dict]:
    hits: list[dict] = []
    vectors = load_drift_vectors(REPO_ROOT).get("vectors") or []
    registry = load_decision_registry(REPO_ROOT)
    staged = staged_paths if staged_paths is not None else _staged_paths()
    staged_basenames = {pathlib.Path(p).name for p in staged}

    for vector in vectors:
        if not isinstance(vector, dict):
            continue
        vid = vector.get("id", "UNKNOWN")

        for pattern in vector.get("trigger_patterns") or []:
            # Filename-like patterns only fire when that file is actually staged
            # (avoids false positives from docs mentioning DECISION_REGISTRY.yaml).
            if re.fullmatch(r"[\w./-]+\.(ya?ml|json|md)", pattern or "", flags=re.IGNORECASE):
                base = pathlib.Path(pattern).name
                if base not in staged_basenames and pattern.replace("\\", "/") not in staged:
                    continue
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    hits.append({"id": vid, "match": pattern, "type": "pattern"})
            except re.error:
                if pattern.lower() in text.lower():
                    hits.append({"id": vid, "match": pattern, "type": "pattern"})

        linked = vector.get("linked_decision")
        if linked:
            for decision_id, keyword, status in active_resurrection_keywords(registry):
                if decision_id != linked:
                    continue
                if keyword.lower() in text.lower():
                    hits.append({"id": vid, "match": keyword, "type": "decision_keyword", "decision": decision_id})

    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diff", action="store_true")
    parser.add_argument("--text", default="")
    args = parser.parse_args()

    content = args.text if args.text else extract_added_lines(_git_diff(staged=not args.diff))
    if not content.strip():
        print("[drift-vector] OK: no content to scan")
        return 0

    hits = scan(content, staged_paths=_staged_paths() if not args.text else [])
    if not hits:
        print("[drift-vector] OK: no drift vectors detected")
        return 0

    print("[drift-vector] WARN: potential drift detected:")
    seen = set()
    for hit in hits:
        key = (hit["id"], hit["match"])
        if key in seen:
            continue
        seen.add(key)
        extra = f" (via {hit['decision']})" if hit.get("decision") else ""
        print(f"  - {hit['id']}: matched '{hit['match']}'{extra}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
