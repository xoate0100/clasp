#!/usr/bin/env python3
"""Detect hub vs spoke governance scope for pre-commit hooks."""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
from functools import lru_cache
from typing import Optional

HUB_REPO_NAMES = frozenset({"project_initializer"})
HUB_REPO_SLUG = "xoate0100/project_initializer"


def _normalize_slug(slug: str) -> str:
    slug = slug.strip().rstrip("/")
    slug = re.sub(r"\.git$", "", slug, flags=re.IGNORECASE)
    return slug


@lru_cache(maxsize=1)
def get_origin_repo_slug(cwd: Optional[str] = None) -> Optional[str]:
    """Return owner/repo or repo name from git origin, if configured."""
    root = pathlib.Path(cwd or ".").resolve()
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    if not out:
        return None

    # https://github.com/owner/repo.git or git@github.com:owner/repo.git
    ssh = re.search(r"[:/]([^/]+)/([^/]+?)(?:\.git)?$", out)
    if ssh:
        return _normalize_slug(f"{ssh.group(1)}/{ssh.group(2)}")

    name = pathlib.Path(out).name
    return _normalize_slug(name) if name else None


def governance_scope_override() -> Optional[str]:
    """Optional explicit scope: hub | spoke (for tests/CI)."""
    raw = os.environ.get("GOVERNANCE_SCOPE", "").strip().lower()
    if raw in ("hub", "spoke"):
        return raw
    return None


def is_hub_repo(cwd: Optional[str] = None) -> bool:
    """True when this checkout is the meta-framework hub (project_initializer)."""
    override = governance_scope_override()
    if override == "hub":
        return True
    if override == "spoke":
        return False

    slug = get_origin_repo_slug(cwd)
    if not slug:
        return False
    if slug in HUB_REPO_NAMES or slug.endswith("/project_initializer"):
        return True
    return slug == HUB_REPO_SLUG


def hub_task_gates_apply(cwd: Optional[str] = None) -> bool:
    """
    Hub ACTIVE_PLAN / INTENT / task-scope gates apply only on the hub repo.
    Spokes run structural validators but not hub plan-pointer enforcement.
    """
    return is_hub_repo(cwd)


def scope_label(cwd: Optional[str] = None) -> str:
    return "hub" if is_hub_repo(cwd) else "spoke"
