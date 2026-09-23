#!/usr/bin/env python3
"""Type and static analysis for backend/frontend when present."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from pre_commit_utils import PIP_TIMEOUT, SUBPROCESS_TIMEOUT, TEST_TIMEOUT, run_subprocess  # noqa: E402


def main() -> int:
    status = 0

    if Path("backend").is_dir():
        pip = run_subprocess(
            [sys.executable, "-m", "pip", "install", "--quiet", "flake8", "mypy"],
            timeout=PIP_TIMEOUT,
        )
        if pip.returncode != 0:
            return pip.returncode

        flake8 = run_subprocess(
            [sys.executable, "-m", "flake8", "backend"],
            timeout=SUBPROCESS_TIMEOUT * 4,
        )
        if flake8.returncode != 0:
            status = 1

        mypy = run_subprocess(
            [sys.executable, "-m", "mypy", "backend"],
            timeout=SUBPROCESS_TIMEOUT * 4,
        )
        if mypy.returncode != 0:
            status = 1

    frontend_pkg = Path("frontend/package.json")
    if frontend_pkg.is_file():
        npm_ci = run_subprocess(
            ["npm", "ci", "--silent"],
            cwd="frontend",
            timeout=PIP_TIMEOUT,
        )
        if npm_ci.returncode != 0:
            status = 1
        else:
            typecheck = run_subprocess(
                ["npm", "run", "-s", "typecheck"],
                cwd="frontend",
                timeout=TEST_TIMEOUT,
            )
            if typecheck.returncode != 0:
                build = run_subprocess(
                    ["npm", "run", "-s", "build", "--if-present"],
                    cwd="frontend",
                    timeout=TEST_TIMEOUT,
                )
                if build.returncode != 0:
                    status = 1

    if status != 0:
        print("[static-analysis] FAILED")
        return 1

    print("[static-analysis] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
