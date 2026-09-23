#!/usr/bin/env python3
"""Security scan for secret-like patterns in staged files."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from pre_commit_utils import MAX_FILE_SIZE, files_from_argv_or_staged, norm_path, run_subprocess  # noqa: E402

SECRET_PATTERN = re.compile(
    r"(AWS_SECRET|BEGIN RSA PRIVATE KEY|password\s*=|api_key\s*=)",
    re.IGNORECASE,
)


def scan_staged_files(files: list[str]) -> list[str]:
    hits: list[str] = []
    for file_path in files:
        fwd = norm_path(file_path)
        if fwd.endswith(".md"):
            continue
        path = Path(file_path)
        if not path.is_file() or path.stat().st_size > MAX_FILE_SIZE:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if SECRET_PATTERN.search(line):
                hits.append(f"{fwd}:{idx}")
    return hits


def main() -> int:
    files = files_from_argv_or_staged(sys.argv)
    hits = scan_staged_files(files)
    if hits:
        print("[security-scan] Secret-like patterns found:")
        for hit in hits[:20]:
            print(f"  - {hit}")
        return 1

    if os.environ.get("RUN_NPM_AUDIT") == "1" and Path("frontend/package.json").is_file():
        audit = run_subprocess(
            ["npm", "audit", "--audit-level=high"],
            cwd="frontend",
            timeout=60,
        )
        if audit.returncode != 0:
            print("[security-scan] npm audit reported issues")
            return audit.returncode

    print("[security-scan] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
