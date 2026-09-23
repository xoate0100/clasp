#!/usr/bin/env python3
"""
Guided initialization wizard (template-generic).

Purpose:
  - Reduce structure mismatches by generating/refreshing PROJECT_LAYOUT in MVP_SPECIFICATION.yaml
  - Prefer non-interactive, deterministic behavior so AI agents can bootstrap autonomously

How it works:
  - Detect markers (apps/, packages/, Next.js markers, src/, etc.)
  - Choose a preset (unless explicitly provided)
  - Write PROJECT_LAYOUT.components + PROJECT_LAYOUT.adaptation into MVP_SPECIFICATION.yaml
  - Persist a summary to 6_ai_runtime_context/INIT_WIZARD_RESULT.yaml for AI/stateful consumption
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional


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


def _load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except Exception as e:
        raise RuntimeError("PyYAML is required for init_wizard.py") from e
    return yaml.safe_load(path.read_text(encoding="utf-8", errors="replace")) or {}


def _dump_yaml(obj: dict, path: Path) -> None:
    import yaml  # type: ignore
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(obj, sort_keys=False, default_flow_style=False), encoding="utf-8")


def _detect_markers(root: Path) -> Dict[str, bool]:
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


def _choose_preset(markers: Dict[str, bool]) -> str:
    # Explicit canonical layout already present
    if markers["has_frontend_dir"] or markers["has_backend_dir"] or markers["has_shared_dir"]:
        return "template_canonical"

    # Workspace-style monorepo
    if markers["has_apps_dir"] and markers["has_packages_dir"]:
        return "apps_packages"

    # apps/* only
    if markers["has_apps_dir"]:
        return "apps_only"

    # Next.js single app at root
    if markers["has_nextjs_markers"] and markers["has_node_root"]:
        return "nextjs_root"

    # Backend-only repo
    if markers["has_python_root"] and not markers["has_node_root"]:
        return "backend_root"

    # src-only library
    if markers["has_src_dir"] and not markers["has_node_root"] and not markers["has_python_root"]:
        return "src_library"

    return "custom_minimal"


def _preset_components(root: Path, preset: str) -> Dict[str, dict]:
    """
    Returns PROJECT_LAYOUT.components mapping with directories and optional hints.
    Directories are directory prefixes with trailing slashes, or "./" for repo root.
    """
    def d(p: str) -> str:
        p = p.strip().replace("\\", "/")
        if p in (".", "./"):
            return "./"
        return p if p.endswith("/") else p + "/"

    if preset == "template_canonical":
        out: Dict[str, dict] = {}
        if (root / "frontend").exists():
            out["frontend"] = {"directories": [d("frontend/")]}
        if (root / "backend").exists():
            out["backend"] = {"directories": [d("backend/")]}
        if (root / "shared").exists():
            out["shared"] = {"directories": [d("shared/")]}
        return out or {"frontend": {"directories": [d("frontend/")]}}

    if preset == "apps_packages":
        out: Dict[str, dict] = {}
        if (root / "apps" / "web").exists():
            out["frontend"] = {"directories": [d("apps/web/")], "framework": "nextjs"}
        else:
            out["frontend"] = {"directories": [d("apps/web/")]}
        if (root / "apps" / "api").exists():
            out["backend"] = {"directories": [d("apps/api/")]}
        if (root / "packages" / "shared").exists():
            out["shared"] = {"directories": [d("packages/shared/")]}
        return out

    if preset == "apps_only":
        out: Dict[str, dict] = {}
        # Prefer common app names
        if (root / "apps" / "web").exists():
            out["frontend"] = {"directories": [d("apps/web/")]}
        elif (root / "apps").exists():
            out["frontend"] = {"directories": [d("apps/")]}
        if (root / "apps" / "api").exists():
            out["backend"] = {"directories": [d("apps/api/")]}
        return out

    if preset == "nextjs_root":
        return {"frontend": {"directories": [d("./")], "framework": "nextjs"}}

    if preset == "backend_root":
        return {"backend": {"directories": [d("./")]}}

    if preset == "src_library":
        return {"shared": {"directories": [d("src/")]}}

    # custom_minimal
    return {"frontend": {"directories": [d("./")]}}


def _merge_project_layout(mvp: dict, project_layout: dict) -> dict:
    out = dict(mvp)
    out["PROJECT_LAYOUT"] = project_layout
    return out


def _normalize_dir(p: str) -> str:
    p = str(p).strip().replace("\\", "/")
    if p in (".", "./"):
        return "./"
    return p if p.endswith("/") else p + "/"


def _apply_answers(project_layout: dict, answers: dict) -> dict:
    """
    Apply answers-file overrides onto a PROJECT_LAYOUT dict.

    Supported keys (all optional):
      preset: string
      adaptation:
        mode: adopt_existing|normalize_to_template
        auto_apply: bool
      components:
        <name>:
          directories: [..]
          language/framework: optional hints
      write_paths: [..]   # directory prefixes
    """
    out = dict(project_layout) if isinstance(project_layout, dict) else {}
    if not isinstance(answers, dict):
        return out

    # adaptation overrides
    adapt = answers.get("adaptation")
    if isinstance(adapt, dict):
        mode = adapt.get("mode")
        auto_apply = adapt.get("auto_apply")
        merged = dict(out.get("adaptation") or {}) if isinstance(out.get("adaptation"), dict) else {}
        if isinstance(mode, str) and mode.strip():
            merged["mode"] = mode.strip()
        if isinstance(auto_apply, bool):
            merged["auto_apply"] = auto_apply
        if merged:
            out["adaptation"] = merged

    # components overrides (explicitly replace)
    comps = answers.get("components")
    if isinstance(comps, dict) and comps:
        new_comps: Dict[str, dict] = {}
        for name, cfg in comps.items():
            if not isinstance(cfg, dict):
                continue
            dirs = cfg.get("directories", [])
            if not isinstance(dirs, list) or not dirs:
                continue
            new_cfg = dict(cfg)
            new_cfg["directories"] = [_normalize_dir(d) for d in dirs if str(d).strip()]
            new_comps[str(name)] = new_cfg
        if new_comps:
            out["components"] = new_comps

    # explicit write_paths
    wp = answers.get("write_paths")
    if isinstance(wp, list) and wp:
        out["write_paths"] = [_normalize_dir(p) for p in wp if str(p).strip()]

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mvp", default="0_phase0_bootstrap/MVP_SPECIFICATION.yaml")
    ap.add_argument(
        "--answers",
        default="",
        help="Optional answers YAML (declarative overrides). If present, it is applied non-interactively.",
    )
    ap.add_argument("--preset", default="", help="Optional preset override.")
    ap.add_argument("--mode", default="", help="Override PROJECT_LAYOUT.adaptation.mode (adopt_existing|normalize_to_template).")
    ap.add_argument("--auto_apply", action="store_true", help="Set PROJECT_LAYOUT.adaptation.auto_apply=true")
    ap.add_argument("--non_interactive", action="store_true", help="Non-interactive mode (default behavior).")
    args = ap.parse_args()

    root = Path(".").resolve()
    mvp_path = (root / args.mvp).resolve()
    runtime_result = root / "6_ai_runtime_context" / "INIT_WIZARD_RESULT.yaml"

    mvp = _load_yaml(mvp_path) if mvp_path.exists() else {}
    markers = _detect_markers(root)

    answers_path = (root / args.answers).resolve() if args.answers.strip() else None
    answers = _load_yaml(answers_path) if answers_path and answers_path.exists() else None

    preset = args.preset.strip() or (str(answers.get("preset")).strip() if isinstance(answers, dict) and answers.get("preset") else "") or _choose_preset(markers)
    components = _preset_components(root, preset)

    # Compute adaptation settings (defaults)
    existing_pl = mvp.get("PROJECT_LAYOUT", {}) if isinstance(mvp, dict) else {}
    existing_adapt = existing_pl.get("adaptation", {}) if isinstance(existing_pl, dict) else {}
    mode = args.mode.strip() or (existing_adapt.get("mode") if isinstance(existing_adapt, dict) else "") or "adopt_existing"
    auto_apply = bool(args.auto_apply) or (bool(existing_adapt.get("auto_apply")) if isinstance(existing_adapt, dict) else False)

    # Never enable auto_apply unless explicitly requested or already set; keep contained by default.
    project_layout = dict(existing_pl) if isinstance(existing_pl, dict) else {}
    project_layout["adaptation"] = {"mode": mode, "auto_apply": auto_apply}

    # Only overwrite components if missing or empty (guided creation); keep user-provided mappings stable.
    existing_components = project_layout.get("components")
    if not (isinstance(existing_components, dict) and existing_components):
        project_layout["components"] = components

    # Apply answers overrides last (explicit > inferred)
    if isinstance(answers, dict):
        project_layout = _apply_answers(project_layout, answers)

    updated = _merge_project_layout(mvp, project_layout)
    _dump_yaml(updated, mvp_path)

    _dump_yaml(
        {
            "version": "1.0",
            "preset": preset,
            "markers": markers,
            "answers_file": str(Path(args.answers).as_posix()) if args.answers.strip() else "",
            "written": {
                "mvp_file": str(Path(args.mvp).as_posix()),
                "project_layout": project_layout,
            },
        },
        runtime_result,
    )

    effective_adapt = project_layout.get("adaptation", {}) if isinstance(project_layout, dict) else {}
    eff_mode = effective_adapt.get("mode", mode)
    eff_auto = effective_adapt.get("auto_apply", auto_apply)
    print(f"[wizard] OK: preset={preset} mode={eff_mode} auto_apply={str(bool(eff_auto)).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
