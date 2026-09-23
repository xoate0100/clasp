#!/usr/bin/env python3
"""
Layout adaptor (Phase 0/1/2)

Goal: reduce repo-template mismatch by:
  Phase 0: Detect current repo structure and emit a plan file
  Phase 1: Decide adopt_existing vs normalize_to_template based on MVP spec
  Phase 2: Optionally apply safe moves when explicitly enabled

Defaults are conservative:
  - If not explicitly configured, it only writes a proposal plan.
  - It never touches meta-framework/standards/ci/schema directories.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PROTECTED_TOP_LEVEL = {
    "0_phase0_bootstrap",
    "1_global_standards",
    "2_framework_templates",
    "3_bootstrap_scripts",
    "4_docs_index",
    "5_reference_architectures",
    "6_ai_runtime_context",
    "7_schemas",
    "8_ci",
    ".github",
}

NO_MOVE_DIRS = PROTECTED_TOP_LEVEL | {"node_modules", ".git", ".next", "dist", "build", "out", ".venv", "venv", "__pycache__"}


def _load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except Exception as e:
        raise RuntimeError("PyYAML is required for layout_adaptor.py") from e
    return yaml.safe_load(path.read_text(encoding="utf-8", errors="replace")) or {}


def _dump_yaml(obj: dict, path: Path) -> None:
    import yaml  # type: ignore
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(obj, sort_keys=False, default_flow_style=False), encoding="utf-8")


def _is_git_repo(root: Path) -> bool:
    return (root / ".git").exists()


def _git_clean(root: Path) -> bool:
    try:
        out = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(root), text=True)
        return out.strip() == ""
    except Exception:
        return False


def _detect_markers(root: Path) -> Dict[str, bool]:
    """
    Lightweight, generic structure detection. Avoid framework-specific deep logic.
    """
    def exists(p: str) -> bool:
        return (root / p).exists()

    return {
        "has_frontend_dir": exists("frontend"),
        "has_backend_dir": exists("backend"),
        "has_shared_dir": exists("shared"),
        "has_apps_dir": exists("apps"),
        "has_packages_dir": exists("packages"),
        "has_src_dir": exists("src"),
        "has_nextjs_markers": exists("next.config.js") or exists("next.config.mjs") or exists("app") or exists("pages"),
        "has_node_root": exists("package.json"),
        "has_python_root": exists("pyproject.toml") or exists("requirements.txt"),
        "has_dotnet_root": any(root.glob("*.sln")),
    }


def _suggest_component_roots(root: Path, markers: Dict[str, bool]) -> Dict[str, List[str]]:
    """
    Suggest component roots if PROJECT_LAYOUT.components is missing or empty.
    This is intentionally heuristic-based and should be treated as a suggestion.
    """
    # If template canonical exists, keep it.
    if markers["has_frontend_dir"] or markers["has_backend_dir"] or markers["has_shared_dir"]:
        out: Dict[str, List[str]] = {}
        if markers["has_frontend_dir"]:
            out["frontend"] = ["frontend/"]
        if markers["has_backend_dir"]:
            out["backend"] = ["backend/"]
        if markers["has_shared_dir"]:
            out["shared"] = ["shared/"]
        return out

    # Common monorepo layouts
    if markers["has_apps_dir"]:
        # Prefer apps/web and apps/api conventions when present.
        out = {}
        if (root / "apps" / "web").exists():
            out["frontend"] = ["apps/web/"]
        if (root / "apps" / "api").exists() or (root / "apps" / "backend").exists():
            out["backend"] = ["apps/api/"] if (root / "apps" / "api").exists() else ["apps/backend/"]
        if markers["has_packages_dir"] and (root / "packages" / "shared").exists():
            out["shared"] = ["packages/shared/"]
        return out or {"frontend": ["apps/web/"]}

    # Next.js single-app at repo root (app/pages + package.json)
    if markers["has_nextjs_markers"] and markers["has_node_root"]:
        return {"frontend": ["./"]}

    # Backend-only repo root
    if markers["has_python_root"]:
        return {"backend": ["./"]}

    # src-only repo (common for libs)
    if markers["has_src_dir"]:
        return {"shared": ["src/"]}

    return {}


def _plan_moves_for_normalization(root: Path, component_dirs: Dict[str, List[str]]) -> List[dict]:
    """
    Build a list of safe move operations to normalize into template canonical dirs.
    Only supports moving top-level dirs into frontend/backend/shared.
    """
    ops: List[dict] = []

    def add_move(src: str, dest: str, reason: str) -> None:
        ops.append({"op": "move_dir", "src": src, "dest": dest, "reason": reason})

    # Only attempt when component dirs are specific directories (not ./)
    for comp, dirs in component_dirs.items():
        if comp not in ("frontend", "backend", "shared"):
            continue
        for d in dirs:
            dnorm = d.replace("\\", "/").strip()
            if dnorm in ("./", "/"):
                continue
            # normalize_to_template means "put this dir's contents under <comp>/"
            # Example: apps/web/ -> frontend/
            if dnorm == f"{comp}/":
                continue
            # Only allow moves of existing directories
            src_dir = (root / dnorm.rstrip("/"))
            if not src_dir.exists() or not src_dir.is_dir():
                continue
            # Block moving protected dirs
            top = dnorm.split("/", 1)[0]
            if top in NO_MOVE_DIRS:
                continue
            add_move(dnorm, f"{comp}/", f"Normalize '{dnorm}' into canonical '{comp}/'")

    return ops


def _apply_move_dir(root: Path, src: str, dest: str, use_git: bool) -> Tuple[bool, str]:
    src_path = (root / src.rstrip("/")).resolve()
    dest_path = (root / dest.rstrip("/")).resolve()

    if not src_path.exists() or not src_path.is_dir():
        return False, f"Source dir does not exist: {src}"
    if dest_path.exists() and any(dest_path.iterdir()):
        return False, f"Destination exists and is non-empty: {dest}"

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if use_git and _is_git_repo(root):
        try:
            subprocess.check_call(["git", "mv", str(src_path), str(dest_path)], cwd=str(root))
            return True, f"git mv {src} -> {dest}"
        except Exception as e:
            return False, f"git mv failed: {e}"

    try:
        shutil.move(str(src_path), str(dest_path))
        return True, f"moved {src} -> {dest}"
    except Exception as e:
        return False, f"move failed: {e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mvp", default="0_phase0_bootstrap/MVP_SPECIFICATION.yaml")
    ap.add_argument("--out", default="6_ai_runtime_context/LAYOUT_REARRANGEMENT_PLAN.yaml")
    ap.add_argument("--apply", action="store_true", help="Apply planned moves (Phase 2).")
    ap.add_argument("--non_interactive", action="store_true", help="Never prompt; fail/skip instead.")
    args = ap.parse_args()

    root = Path(".").resolve()
    mvp_path = (root / args.mvp).resolve()
    out_path = (root / args.out).resolve()

    mvp = _load_yaml(mvp_path) if mvp_path.exists() else {}
    markers = _detect_markers(root)

    project_layout = mvp.get("PROJECT_LAYOUT", {}) if isinstance(mvp, dict) else {}
    adaptation = project_layout.get("adaptation", {}) if isinstance(project_layout, dict) else {}
    mode = adaptation.get("mode", "adopt_existing") if isinstance(adaptation, dict) else "adopt_existing"
    auto_apply = bool(adaptation.get("auto_apply")) if isinstance(adaptation, dict) else False

    components_cfg = (project_layout.get("components") if isinstance(project_layout, dict) else None) or {}
    has_components_cfg = isinstance(components_cfg, dict) and bool(components_cfg)

    suggested_components = _suggest_component_roots(root, markers) if not has_components_cfg else {}

    # Decide component_dirs used for planning normalization
    component_dirs: Dict[str, List[str]] = {}
    if has_components_cfg:
        for comp, cfg in components_cfg.items():
            if not isinstance(cfg, dict):
                continue
            dirs = cfg.get("directories", [])
            if isinstance(dirs, list):
                component_dirs[comp] = [str(d) for d in dirs if str(d).strip()]
    else:
        component_dirs = suggested_components

    planned_ops = _plan_moves_for_normalization(root, component_dirs) if mode == "normalize_to_template" else []

    plan = {
        "version": "1.0",
        "detected": {"markers": markers},
        "decision": {"mode": mode, "auto_apply": auto_apply, "will_apply": bool(args.apply or auto_apply)},
        "suggestions": {"project_layout_components": suggested_components},
        "operations": planned_ops,
        "safety": {
            "requires_git_clean": True,
            "protected_top_level": sorted(PROTECTED_TOP_LEVEL),
            "no_move_dirs": sorted(NO_MOVE_DIRS),
        },
        "results": [],
    }

    # Always write plan (Phase 0)
    _dump_yaml(plan, out_path)

    # Phase 1: decide and optionally apply
    if not planned_ops:
        return 0

    will_apply = bool(args.apply) or auto_apply
    if not will_apply:
        return 0

    # Phase 2: apply safely
    if not _is_git_repo(root):
        # ok, but less safe
        pass

    if plan["safety"]["requires_git_clean"] and _is_git_repo(root) and not _git_clean(root):
        print("[layout] BLOCKING: git working tree not clean; refusing to apply moves.")
        return 2

    results = []
    for op in planned_ops:
        if op.get("op") != "move_dir":
            results.append({"ok": False, "op": op, "message": "Unsupported op"})
            continue
        ok, msg = _apply_move_dir(root, op["src"], op["dest"], use_git=True)
        results.append({"ok": ok, "op": op, "message": msg})

    plan["results"] = results
    _dump_yaml(plan, out_path)

    if not all(r["ok"] for r in results):
        print("[layout] Some operations failed; see plan file for details.")
        return 3

    print("[layout] OK: applied normalization operations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
