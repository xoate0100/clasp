#!/usr/bin/env python3
"""
crosswalk — onboard / upgrade a repo against the hub (COMMAND_INTERFACE §4.8).

Idempotent: already-onboarded repos exit 0 with a no-op report.
Unknown / missing adapter selection → adapters/generic.
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
from typing import Optional

try:
    import yaml
except ImportError:
    print("[crosswalk] ERROR: PyYAML required", file=sys.stderr)
    sys.exit(3)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SEL_REL = pathlib.Path("0_phase0_bootstrap") / "stack_adapter.yaml"
VER_REL = pathlib.Path("0_phase0_bootstrap") / "META_FRAMEWORK_VERSION.yaml"


def parse_adapter_id(sel_path: pathlib.Path) -> Optional[str]:
    if not sel_path.exists():
        return None
    data = yaml.safe_load(sel_path.read_text(encoding="utf-8")) or {}
    if isinstance(data, dict) and data.get("adapter"):
        return str(data["adapter"]).strip()
    return None


def write_adapter_selection(root: pathlib.Path, adapter_id: str) -> None:
    sel = root / SEL_REL
    sel.parent.mkdir(parents=True, exist_ok=True)
    body = (
        f"# Active stack adapter selection\n"
        f"adapter: {adapter_id}\n"
        f"manifest: adapters/{adapter_id}/stack_adapter.yaml\n"
    )
    sel.write_text(body, encoding="utf-8")


def adapter_manifest_exists(root: pathlib.Path, adapter_id: str) -> bool:
    return (root / "adapters" / adapter_id / "stack_adapter.json").is_file()


def is_onboarded(root: pathlib.Path) -> bool:
    """Already aligned: selection + version + adapter manifest present."""
    sel = root / SEL_REL
    ver = root / VER_REL
    if not sel.is_file() or not ver.is_file():
        return False
    adapter_id = parse_adapter_id(sel)
    if not adapter_id:
        return False
    return adapter_manifest_exists(root, adapter_id)


def ensure_version_stub(root: pathlib.Path) -> None:
    """Seed a minimal version manifest when missing (greenfield / generic)."""
    ver = root / VER_REL
    if ver.is_file():
        return
    hub = root / VER_REL
    # Prefer copying from this hub checkout when available
    src = REPO_ROOT / VER_REL
    ver.parent.mkdir(parents=True, exist_ok=True)
    if src.is_file() and src.resolve() != ver.resolve():
        shutil.copy2(src, ver)
        return
    ver.write_text(
        'template_version: "0.0.0"\n'
        'template_repo: "https://github.com/xoate0100/project_initializer.git"\n'
        'installed_at: "1970-01-01T00:00:00Z"\n'
        'last_updated_at: "1970-01-01T00:00:00Z"\n'
        "update_history: []\n",
        encoding="utf-8",
    )


def resolve_target_adapter(root: pathlib.Path, override: Optional[str]) -> str:
    if override:
        return override
    existing = parse_adapter_id(root / SEL_REL)
    if existing and adapter_manifest_exists(root, existing):
        return existing
    if adapter_manifest_exists(root, "generic"):
        return "generic"
    if adapter_manifest_exists(root, "python"):
        return "python"
    return "generic"


def hub_reachable(root: pathlib.Path) -> bool:
    ver = root / VER_REL
    url = "https://github.com/xoate0100/project_initializer.git"
    if ver.is_file():
        try:
            data = yaml.safe_load(ver.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict) and data.get("template_repo"):
                url = str(data["template_repo"])
        except Exception:
            pass
    try:
        r = subprocess.run(
            ["git", "ls-remote", "--heads", url],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return r.returncode == 0
    except Exception:
        return False


def run_crosswalk(
    root: pathlib.Path,
    *,
    adapter: Optional[str] = None,
    dry_run: bool = False,
    offline: bool = False,
    force: bool = False,
) -> int:
    root = root.resolve()
    if is_onboarded(root) and not force:
        aid = parse_adapter_id(root / SEL_REL)
        print(f"[crosswalk] already aligned (adapter={aid}) — idempotent no-op")
        return 0

    target = resolve_target_adapter(root, adapter)
    if not adapter_manifest_exists(root, target) and target != "generic":
        print(
            f"[crosswalk] adapter '{target}' manifest missing; falling back to generic",
            file=sys.stderr,
        )
        target = "generic"

    if not adapter_manifest_exists(root, target):
        print(
            f"[crosswalk] FATAL: adapters/{target}/stack_adapter.json missing",
            file=sys.stderr,
        )
        return 3

    if dry_run:
        print(f"[crosswalk] dry-run: would select adapter={target}")
        print(f"[crosswalk] dry-run: would write {SEL_REL.as_posix()}")
        return 0

    write_adapter_selection(root, target)
    ensure_version_stub(root)

    if not offline and not hub_reachable(root):
        print("[crosswalk] hub unreachable (exit 4)", file=sys.stderr)
        return 4

    print(f"[crosswalk] OK adapter={target} (subsumed init+check-updates+apply-updates)")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", help="Force adapter id (default: detect or generic)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--offline", action="store_true", help="Skip hub reachability check")
    parser.add_argument("--force", action="store_true", help="Re-run even if already onboarded")
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root (default: cwd)",
    )
    args = parser.parse_args(argv)
    return run_crosswalk(
        pathlib.Path(args.root),
        adapter=args.adapter,
        dry_run=args.dry_run,
        offline=args.offline,
        force=args.force,
    )


if __name__ == "__main__":
    raise SystemExit(main())
