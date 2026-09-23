#!/usr/bin/env python3
"""Shared utilities for cross-platform pre-commit bootstrap hooks."""

from __future__ import annotations

import pathlib
import subprocess
from typing import List

REPO_ROOT = pathlib.Path(".").resolve()

STANDARD_EXCLUDED_DIRS = {
    "node_modules",
    ".next",
    "__pycache__",
    ".git",
    "venv",
    ".venv",
    "dist",
    "build",
    ".coverage",
    "coverage-backend.dat",
}

MAX_FILE_SIZE = 1 << 20
MAX_FILES_TO_PROCESS = 1000
SUBPROCESS_TIMEOUT = 30
GIT_TIMEOUT = 30
PIP_TIMEOUT = 120
FORMAT_TIMEOUT = 120
TEST_TIMEOUT = 300


def norm_path(path: str) -> str:
    return str(path).replace("\\", "/")


def skip_artifact(path: str) -> bool:
    parts = set(norm_path(path).split("/"))
    return bool(parts & STANDARD_EXCLUDED_DIRS)


def run_subprocess(cmd: List[str], timeout: int = SUBPROCESS_TIMEOUT, **kwargs):
    try:
        return subprocess.run(cmd, timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired:
        print(f"[pre-commit] TIMEOUT after {timeout}s: {' '.join(cmd)}")
        raise


def get_staged_files(timeout: int = GIT_TIMEOUT) -> List[str]:
    try:
        output = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            text=True,
            timeout=timeout,
        )
        return [norm_path(line.strip()) for line in output.splitlines() if line.strip()]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []


def files_from_argv_or_staged(argv: List[str]) -> List[str]:
    if len(argv) > 1:
        files = [norm_path(arg) for arg in argv[1:] if arg and not arg.startswith("-")]
    else:
        files = get_staged_files()
    filtered = [path for path in files if not skip_artifact(path)]
    return filtered[:MAX_FILES_TO_PROCESS]
