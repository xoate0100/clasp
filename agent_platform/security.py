"""Path safety and trust hierarchy enforcement."""

from __future__ import annotations

import os
import pathlib
import re

SECRET_PATTERNS = re.compile(
    r"(password|api[_-]?key|secret|token|BEGIN RSA PRIVATE KEY)",
    re.IGNORECASE,
)

EXCLUDED_SCAN_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
}


def norm_path(path: str | pathlib.Path) -> str:
    return str(path).replace("\\", "/")


def is_within_root(root: pathlib.Path, target: pathlib.Path) -> bool:
    try:
        target.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def safe_resolve(root: pathlib.Path, relative: str) -> pathlib.Path | None:
    candidate = (root / relative).resolve()
    if not is_within_root(root, candidate):
        return None
    if candidate.is_symlink():
        return None
    return candidate


def sanitize_log_text(text: str) -> str:
    return SECRET_PATTERNS.sub("[REDACTED]", text)


def should_skip_dir(name: str) -> bool:
    return name in EXCLUDED_SCAN_DIRS


def load_trust_hierarchy() -> list[str]:
    return [
        "hard_system_safety",
        "initializer_governance",
        "organization_policy",
        "child_repository_policy",
        "task_instructions",
        "repository_content",
    ]
