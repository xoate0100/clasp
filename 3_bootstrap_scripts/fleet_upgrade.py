#!/usr/bin/env python3
"""
Fleet upgrade driver — ratchet children onto the hub via FLEET_LEDGER.yaml.

Defaults to PR mode (never pushes to main/master). Dry-run prints the plan and
writes nothing. Resumable: a failed repo does not block the rest.
"""

from __future__ import annotations

import argparse
import copy
import json
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Optional

try:
    import yaml
    import jsonschema
except ImportError:
    print("[fleet-upgrade] ERROR: PyYAML and jsonschema required", file=sys.stderr)
    sys.exit(3)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_LEDGER = REPO_ROOT / "5_reference_architectures" / "FLEET_LEDGER.yaml"
SCHEMA_PATH = REPO_ROOT / "7_schemas" / "fleet_ledger.schema.json"

DEFAULT_BRANCHES = frozenset({"main", "master"})
DEFAULT_MODE = "pr"


class FleetUpgradeError(Exception):
    """Per-repo or configuration failure."""


def load_ledger(path: pathlib.Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise FleetUpgradeError(f"ledger must be a mapping: {path}")
    return data


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_ledger(ledger: dict, schema: Optional[dict] = None) -> None:
    schema = schema or load_schema()
    jsonschema.validate(ledger, schema)


def save_ledger(path: pathlib.Path, ledger: dict) -> None:
    ledger = copy.deepcopy(ledger)
    ledger["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    validate_ledger(ledger)
    path.write_text(
        yaml.safe_dump(ledger, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def assert_mode_safe(mode: str, target_branch: str = "main") -> None:
    """Refuse any mode that would push to a default branch."""
    if mode not in ("pr", "push"):
        raise FleetUpgradeError(f"unknown mode: {mode!r}")
    if mode == "push" and target_branch in DEFAULT_BRANCHES:
        raise FleetUpgradeError(
            f"refusing push mode to default branch '{target_branch}' — use --mode pr"
        )


def plan_repo(entry: dict, hub_target: Optional[str]) -> str:
    repo = entry.get("repository", "?")
    adapter = entry.get("adapter", "?")
    runtime = entry.get("governance_runtime", "?")
    product = entry.get("product_stack", "?")
    current = entry.get("hub_version")
    return (
        f"{repo}: adapter={adapter} product_stack={product} "
        f"governance_runtime={runtime} hub={current} -> {hub_target} "
        f"[result={entry.get('result')}]"
    )


def apply_repo_pr_mode(entry: dict, hub_target: Optional[str]) -> dict:
    """
    Record a planned PR-mode upgrade for one repo.

    Does not clone remotes or push. Task 10 executes the live ratchet; this
    updates ledger bookkeeping so the driver is testable and resumable.
    """
    updated = copy.deepcopy(entry)
    updated["result"] = "planned"
    updated["last_error"] = None
    updated["pr_url"] = None
    # Preserve existing fields; mark intent toward hub_target when known
    if hub_target and not updated.get("hub_version"):
        # leave hub_version null until live crosswalk; bookkeeping only
        pass
    updated["last_crosswalk"] = None
    _ = hub_target  # reserved for task 10 live apply
    return updated


ApplyFn = Callable[[dict, Optional[str]], dict]


def run_fleet_upgrade(
    ledger: dict,
    *,
    dry_run: bool = False,
    mode: Optional[str] = None,
    resume: bool = True,
    target_branch: str = "main",
    apply_fn: Optional[ApplyFn] = None,
) -> tuple[dict, list[str]]:
    """
    Process each ledger repo. Returns (updated_ledger, log_lines).

    dry_run: print plan only; return ledger unchanged.
    resume: skip entries already result=ok.
    """
    mode = mode or ledger.get("default_mode") or DEFAULT_MODE
    assert_mode_safe(mode, target_branch)

    hub_target = ledger.get("hub_target_version")
    apply = apply_fn or apply_repo_pr_mode
    logs: list[str] = []
    working = copy.deepcopy(ledger)
    repos = working.get("repos")
    if not isinstance(repos, list):
        raise FleetUpgradeError("ledger.repos must be a list")

    for idx, entry in enumerate(repos):
        if not isinstance(entry, dict):
            logs.append(f"SKIP invalid entry at index {idx}")
            continue
        repo = entry.get("repository", f"index-{idx}")
        line = plan_repo(entry, hub_target)
        if resume and entry.get("result") == "ok":
            logs.append(f"RESUME-SKIP {line}")
            continue

        logs.append(f"PLAN {line} mode={mode}")
        if dry_run:
            continue

        try:
            if mode != "pr":
                # push mode already refused for default branches; other branches
                # still go through apply_fn for symmetry.
                pass
            repos[idx] = apply(entry, hub_target)
            logs.append(f"OK {repo} result={repos[idx].get('result')}")
        except Exception as exc:  # noqa: BLE001 — must not block fleet
            failed = copy.deepcopy(entry)
            failed["result"] = "failed"
            failed["last_error"] = str(exc)
            repos[idx] = failed
            logs.append(f"FAIL {repo}: {exc}")

    return working, logs


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ledger",
        type=pathlib.Path,
        default=DEFAULT_LEDGER,
        help="Path to FLEET_LEDGER.yaml",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan only; do not write the ledger",
    )
    parser.add_argument(
        "--mode",
        choices=["pr", "push"],
        default=None,
        help="Override ledger default_mode (default: pr / ledger value)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not skip repos already marked ok",
    )
    parser.add_argument(
        "--target-branch",
        default="main",
        help="Branch name used for push-mode safety checks (default: main)",
    )
    args = parser.parse_args(argv)

    if not args.ledger.is_file():
        print(f"[fleet-upgrade] missing ledger: {args.ledger}", file=sys.stderr)
        return 2

    try:
        ledger = load_ledger(args.ledger)
        validate_ledger(ledger)
        updated, logs = run_fleet_upgrade(
            ledger,
            dry_run=args.dry_run,
            mode=args.mode,
            resume=not args.no_resume,
            target_branch=args.target_branch,
        )
    except (FleetUpgradeError, jsonschema.ValidationError) as exc:
        print(f"[fleet-upgrade] ERROR: {exc}", file=sys.stderr)
        return 1

    for line in logs:
        print(f"[fleet-upgrade] {line}")

    if args.dry_run:
        print("[fleet-upgrade] dry-run complete — ledger not written")
        return 0

    save_ledger(args.ledger, updated)
    print(f"[fleet-upgrade] wrote {args.ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
