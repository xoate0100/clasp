#!/usr/bin/env python3
"""
Live Wave 0 fleet ratchet — open PR-only crosswalk PRs for FLEET_LEDGER repos.

Requires NA-18 approved. Never merges spoke PRs. Never pushes to main/master.
Hub self-entry is marked ok without an external spoke PR (ledger+report ship on the hub PR).
"""

from __future__ import annotations

import argparse
import copy
import pathlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Optional

try:
    import yaml
except ImportError:
    print("[fleet-ratchet] ERROR: PyYAML required", file=sys.stderr)
    sys.exit(3)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "3_bootstrap_scripts"))

import crosswalk as cw  # noqa: E402
import fleet_upgrade as fu  # noqa: E402

HUB_REPO = "xoate0100/project_initializer"
BRANCH_PREFIX = "wave0-ratchet"
EXIT5 = "exit 5 — needs human review"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(
    cmd: list[str],
    *,
    cwd: Optional[pathlib.Path] = None,
    check: bool = True,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        capture_output=capture,
        text=True,
    )


def _copy_tree(src: pathlib.Path, dst: pathlib.Path) -> None:
    if not src.is_dir():
        raise fu.FleetUpgradeError(f"missing source tree: {src}")
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def sync_adapter_surface(hub: pathlib.Path, clone: pathlib.Path, adapter: str) -> None:
    """Copy adapter manifests needed for crosswalk into the spoke clone."""
    for aid in sorted({adapter, "generic"}):
        src = hub / "adapters" / aid
        if src.is_dir():
            _copy_tree(src, clone / "adapters" / aid)
    # Ensure bootstrap dir exists for selection + version
    (clone / "0_phase0_bootstrap").mkdir(parents=True, exist_ok=True)


def write_product_stack_note(clone: pathlib.Path, entry: dict) -> None:
    note = clone / "docs" / "factory" / "WAVE0_RATCHET_NOTE.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "# Wave 0 ratchet note\n\n"
        f"- repository: `{entry.get('repository')}`\n"
        f"- adapter: `{entry.get('adapter')}`\n"
        f"- product_stack: `{entry.get('product_stack')}` (informational; DEC-0005)\n"
        f"- governance_runtime: `{entry.get('governance_runtime')}`\n"
        f"- hub_target: see hub `FLEET_LEDGER.yaml` / `hub_target_version`\n\n"
        "Opened by `fleet_ratchet.py` under NA-18. **Do not merge without human review.**\n"
        "Full template force-upgrade is out of scope for this PR when exit 5 applies.\n"
    )
    note.write_text(body, encoding="utf-8")


def apply_hub_self(entry: dict, hub_target: Optional[str]) -> dict:
    updated = copy.deepcopy(entry)
    updated["result"] = "ok"
    updated["last_error"] = None
    updated["hub_version"] = hub_target or updated.get("hub_version")
    updated["last_crosswalk"] = _utc_now()
    updated["pr_url"] = None  # hub changes land on the task-10 hub PR
    updated["module_versions"] = updated.get("module_versions") or {
        "hub-placeholder": "0.0.0"
    }
    return updated


def open_spoke_pr(
    entry: dict,
    hub_target: Optional[str],
    *,
    work_root: pathlib.Path,
    hub_root: pathlib.Path,
    dry_run: bool = False,
) -> dict:
    repo = entry["repository"]
    if repo == HUB_REPO:
        return apply_hub_self(entry, hub_target)

    owner, name = repo.split("/", 1)
    clone = work_root / name
    branch = f"{BRANCH_PREFIX}-{hub_target or 'hub'}"
    adapter = str(entry.get("adapter") or "python")
    product = str(entry.get("product_stack") or "unknown")
    runtime = str(entry.get("governance_runtime") or "python")

    if clone.exists():
        shutil.rmtree(clone)

    if dry_run:
        out = copy.deepcopy(entry)
        out["result"] = "planned"
        out["last_error"] = None
        out["pr_url"] = f"https://github.com/{repo}/pull/dry-run"
        return out

    _run(
        [
            "gh",
            "repo",
            "clone",
            repo,
            str(clone),
            "--",
            "--depth",
            "1",
        ]
    )
    _run(["git", "checkout", "-b", branch], cwd=clone)

    sync_adapter_surface(hub_root, clone, adapter)
    write_product_stack_note(clone, entry)

    # Preserve DEC-0005: product_stack is informational; do not infer from runtime
    cw.write_adapter_selection(clone, adapter)
    # Stamp a short sidecar so reviewers see the split explicitly
    sidecar = clone / "0_phase0_bootstrap" / "product_stack.yaml"
    sidecar.write_text(
        f"# Informational only (DEC-0005) — not used for verb dispatch\n"
        f"product_stack: {product}\n"
        f"governance_runtime: {runtime}\n",
        encoding="utf-8",
    )

    rc = cw.run_crosswalk(clone, adapter=adapter, offline=True, force=True)
    updated = copy.deepcopy(entry)
    updated["adapter"] = adapter
    updated["product_stack"] = product
    updated["governance_runtime"] = runtime

    needs_human = False
    human_reasons: list[str] = []
    if rc not in (0,):
        needs_human = True
        human_reasons.append(f"crosswalk returned {rc}")
    if repo == "xoate0100/surewealth-education-platform":
        # NA-13 still blocked — do not attempt Node migration in this PR
        needs_human = True
        human_reasons.append("NA-13 Node migration still blocked")
    if hub_target:
        ver_path = clone / cw.VER_REL
        if ver_path.is_file():
            try:
                ver = yaml.safe_load(ver_path.read_text(encoding="utf-8")) or {}
                current = str(ver.get("template_version") or "")
                updated["hub_version"] = current or None
                if current and current != hub_target:
                    needs_human = True
                    human_reasons.append(
                        f"hub_version {current} != target {hub_target} "
                        "(full template update deferred)"
                    )
            except Exception as exc:  # noqa: BLE001
                needs_human = True
                human_reasons.append(f"version parse: {exc}")

    _run(["git", "-c", "core.safecrlf=false", "add", "-A"], cwd=clone)
    status = _run(["git", "status", "--porcelain"], cwd=clone, check=False)
    if not (status.stdout or "").strip():
        # Still open an empty-change note PR via empty commit for tracking
        _run(
            [
                "git",
                "commit",
                "--allow-empty",
                "-m",
                f"plan:content-factory-wave0-hub-modules component:shared task:10\n\n"
                f"Wave 0 ratchet note for {repo} (no file delta).",
            ],
            cwd=clone,
        )
    else:
        _run(
            [
                "git",
                "commit",
                "-m",
                f"plan:content-factory-wave0-hub-modules component:shared task:10\n\n"
                f"Wave 0 crosswalk ratchet toward hub {hub_target} "
                f"(adapter={adapter}, product_stack={product}).",
            ],
            cwd=clone,
        )

    push = _run(["git", "push", "-u", "origin", branch], cwd=clone, check=False)
    if push.returncode != 0:
        raise fu.FleetUpgradeError(
            f"git push failed: {(push.stderr or push.stdout or '').strip()}"
        )

    body = (
        "## Summary\n"
        f"- Wave 0 fleet ratchet (NA-18) toward hub `{hub_target}`.\n"
        f"- adapter=`{adapter}` product_stack=`{product}` "
        f"governance_runtime=`{runtime}`.\n"
        "- Agent will **not** merge this PR.\n\n"
        "## Human review\n"
    )
    if needs_human:
        body += f"- **{EXIT5}**: " + "; ".join(human_reasons) + "\n"
    else:
        body += "- Crosswalk completed in clone; please review before merge.\n"

    body_file = clone / ".wave0_pr_body.md"
    body_file.write_text(body, encoding="utf-8")

    # Prefer existing open PR on this head if create races / already exists
    existing = _run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--head",
            f"{owner}:{branch}",
            "--json",
            "url",
            "--jq",
            ".[0].url",
        ],
        cwd=clone,
        check=False,
    )
    pr_url = (existing.stdout or "").strip()
    if not pr_url:
        pr = _run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                repo,
                "--head",
                f"{owner}:{branch}",
                "--base",
                "main",
                "--title",
                f"Wave 0 ratchet: crosswalk toward hub {hub_target}",
                "--body-file",
                str(body_file),
            ],
            cwd=clone,
            check=False,
        )
        if pr.returncode != 0:
            # base may be master
            pr = _run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--repo",
                    repo,
                    "--head",
                    f"{owner}:{branch}",
                    "--base",
                    "master",
                    "--title",
                    f"Wave 0 ratchet: crosswalk toward hub {hub_target}",
                    "--body-file",
                    str(body_file),
                ],
                cwd=clone,
                check=False,
            )
        if pr.returncode != 0:
            raise fu.FleetUpgradeError(
                f"gh pr create failed: {(pr.stderr or pr.stdout or '').strip()}"
            )
        pr_url = (pr.stdout or "").strip().splitlines()[-1].strip()
    try:
        body_file.unlink(missing_ok=True)
    except OSError:
        pass

    updated["pr_url"] = pr_url
    updated["last_crosswalk"] = _utc_now()
    if needs_human:
        updated["result"] = "skipped"
        updated["last_error"] = f"{EXIT5}: " + "; ".join(human_reasons)
    else:
        updated["result"] = "ok"
        updated["last_error"] = None
        if hub_target and not updated.get("hub_version"):
            updated["hub_version"] = hub_target
    return updated


def run_live_ratchet(
    ledger: dict,
    *,
    work_root: pathlib.Path,
    hub_root: pathlib.Path,
    dry_run: bool = False,
) -> tuple[dict, list[str]]:
    def apply(entry: dict, hub_target: Optional[str]) -> dict:
        return open_spoke_pr(
            entry,
            hub_target,
            work_root=work_root,
            hub_root=hub_root,
            dry_run=dry_run,
        )

    return fu.run_fleet_upgrade(
        ledger,
        dry_run=False,
        mode="pr",
        resume=True,
        apply_fn=apply,
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ledger",
        type=pathlib.Path,
        default=fu.DEFAULT_LEDGER,
    )
    parser.add_argument(
        "--work-root",
        type=pathlib.Path,
        default=REPO_ROOT / ".fleet_ratchet_work",
        help="Scratch directory for spoke clones",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan live PRs without cloning/pushing",
    )
    args = parser.parse_args(argv)

    ledger = fu.load_ledger(args.ledger)
    fu.validate_ledger(ledger)
    args.work_root.mkdir(parents=True, exist_ok=True)

    updated, logs = run_live_ratchet(
        ledger,
        work_root=args.work_root,
        hub_root=REPO_ROOT,
        dry_run=args.dry_run,
    )
    for line in logs:
        print(f"[fleet-ratchet] {line}")

    if args.dry_run:
        print("[fleet-ratchet] dry-run complete — ledger not written")
        return 0

    fu.save_ledger(args.ledger, updated)
    print(f"[fleet-ratchet] wrote {args.ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
