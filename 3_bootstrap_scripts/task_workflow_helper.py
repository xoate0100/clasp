#!/usr/bin/env python3
"""
Task workflow helper for branch/commit discipline.

Commands:
  start      - create/switch task branch from ACTIVE_TASK_POINTER
  checkpoint - print required checkpoint commit message scaffold
  verify     - verify branch naming and task alignment
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys
from typing import Any

import yaml


POINTER_PATH = pathlib.Path("6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml")
PLAN_PATH = pathlib.Path("6_ai_runtime_context/ACTIVE_PLAN.yaml")


def _run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def _load_yaml(path: pathlib.Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _current_branch() -> str:
    # PR CI uses detached HEAD; use GitHub Actions head branch when available
    gha_head = os.environ.get("GITHUB_HEAD_REF", "").strip()
    if gha_head:
        return gha_head
    ref_name = os.environ.get("GITHUB_REF_NAME", "").strip()
    if ref_name and ref_name != "HEAD":
        return ref_name
    code, out = _run(["git", "branch", "--show-current"])
    if code != 0:
        raise RuntimeError(out)
    return out.strip()


def _task_name(plan: dict[str, Any], task_id: int) -> str:
    for task in plan.get("tasks", []):
        if isinstance(task, dict) and task.get("id") == task_id:
            return str(task.get("name", f"task-{task_id}"))
    return f"task-{task_id}"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def cmd_start(args: argparse.Namespace) -> int:
    pointer = _load_yaml(POINTER_PATH)
    plan = _load_yaml(PLAN_PATH)
    task_id = int(pointer.get("current_task", 0))
    task_label = _slug(_task_name(plan, task_id))
    branch = args.branch or f"feat/task-{task_id}-{task_label}"

    code, out = _run(["git", "fetch", "origin"])
    if code != 0:
        print(out)
        return code
    code, out = _run(["git", "checkout", "-b", branch])
    if code != 0 and "already exists" in out.lower():
        code, out = _run(["git", "checkout", branch])
    if code != 0:
        print(out)
        return code

    print(f"[task-workflow] on branch: {branch}")
    return 0


def cmd_checkpoint(_args: argparse.Namespace) -> int:
    pointer = _load_yaml(POINTER_PATH)
    plan = _load_yaml(PLAN_PATH)
    task_id = int(pointer.get("current_task", 0))
    plan_id = str(plan.get("plan_id", "proposal-system-mvp"))
    component = str(plan.get("component", "frontend"))
    name = _task_name(plan, task_id)
    print(
        f"plan:{plan_id} component:{component} task:{task_id} checkpoint: {name}"
    )
    return 0


def cmd_verify(_args: argparse.Namespace) -> int:
    pointer = _load_yaml(POINTER_PATH)
    task_id = int(pointer.get("current_task", 0))
    branch = _current_branch()
    if branch == "main":
        print("[task-workflow] ERROR: task work is blocked on main branch.")
        return 1
    # Template / fleet ratchet branches are not feature-task branches.
    if branch.startswith("ratchet-") or branch.startswith("wave0-ratchet"):
        print(f"[task-workflow] OK: ratchet branch '{branch}' exempt from task alignment")
        return 0
    if f"task-{task_id}" not in branch:
        print(f"[task-workflow] ERROR: branch '{branch}' does not match current task {task_id}.")
        return 1
    print(f"[task-workflow] OK: branch '{branch}' aligned to task {task_id}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Task workflow helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Create/switch task branch")
    p_start.add_argument("--branch", type=str, default=None)
    p_start.set_defaults(func=cmd_start)

    p_checkpoint = sub.add_parser("checkpoint", help="Print checkpoint commit message")
    p_checkpoint.set_defaults(func=cmd_checkpoint)

    p_verify = sub.add_parser("verify", help="Verify branch/task alignment")
    p_verify.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
