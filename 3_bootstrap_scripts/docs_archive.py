#!/usr/bin/env python3
"""
Documentation archive CLI — deprecate, archive, and validate doc lifecycle.

Usage:
    python 3_bootstrap_scripts/docs_archive.py validate
    python 3_bootstrap_scripts/docs_archive.py deprecate docs/old.md --superseded-by docs/new.md
    python 3_bootstrap_scripts/docs_archive.py archive docs/old.md --superseded-by docs/new.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agentic.doc_governance import archive_document, deprecate_document, validate_doc_governance  # noqa: E402
from agentic.optional_tools import is_tool_enabled  # noqa: E402


def main() -> int:
    if len(sys.argv) == 1:
        sys.argv.append("validate")

    if not is_tool_enabled("doc_lifecycle"):
        print("[docs-archive] SKIP: optional tool disabled")
        return 0

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("validate", help="Validate doc governance rules")

    dep = sub.add_parser("deprecate", help="Mark doc deprecated in place")
    dep.add_argument("path", help="Doc path relative to repo root")
    dep.add_argument("--superseded-by", required=True)

    arc = sub.add_parser("archive", help="Move doc to docs/archive/")
    arc.add_argument("path", help="Doc path relative to repo root")
    arc.add_argument("--superseded-by", required=True)

    args = parser.parse_args()
    command = args.command or "validate"

    if command == "validate":
        errors = validate_doc_governance(REPO_ROOT)
        if errors:
            print("[docs-archive] FAIL:")
            for err in errors:
                print(f"  - {err}")
            return 1
        print("[docs-archive] OK: documentation governance passed")
        return 0

    if command == "deprecate":
        deprecate_document(args.path, args.superseded_by, REPO_ROOT)
        print(f"[docs-archive] OK: deprecated {args.path}")
        return 0

    if command == "archive":
        dest = archive_document(args.path, args.superseded_by, REPO_ROOT)
        print(f"[docs-archive] OK: archived -> {dest.relative_to(REPO_ROOT)}")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
