"""Layer 0 — repository truth and execution environment."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import uuid
from typing import Any

from agent_platform.models import RepositoryProfile
from agent_platform.release import CAPABILITY_SCHEMA_VERSION, read_template_version
from agent_platform.security import norm_path, should_skip_dir

LANG_EXTENSIONS = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cs": "csharp",
}

FRAMEWORK_MARKERS = {
    "package.json": "node",
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "Cargo.toml": "rust",
    "go.mod": "go",
}


def _git(args: list[str], root: pathlib.Path, timeout: int = 30) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass
    return ""


def scan_repository(root: pathlib.Path) -> RepositoryProfile:
    root = root.resolve()
    repo_id = hashlib.sha256(str(root).encode()).hexdigest()[:12]

    languages: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(should_skip_dir(part) for part in path.parts):
            continue
        lang = LANG_EXTENSIONS.get(path.suffix.lower())
        if lang:
            languages.add(lang)

    frameworks: list[str] = []
    for marker, fw in FRAMEWORK_MARKERS.items():
        if (root / marker).exists():
            frameworks.append(fw)

    package_managers: list[str] = []
    if (root / "package.json").exists():
        package_managers.append("npm")
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        package_managers.append("pip")

    ci_workflows = sorted(
        norm_path(str(p.relative_to(root)))
        for p in (root / ".github" / "workflows").glob("*.yml")
        if p.is_file()
    ) if (root / ".github" / "workflows").is_dir() else []

    test_commands = []
    if (root / "backend").is_dir():
        test_commands.append("pytest")
    if (root / "frontend" / "package.json").is_file():
        test_commands.append("npm test")

    manifest_path = root / "0_phase0_bootstrap" / "META_FRAMEWORK_VERSION.yaml"
    protected_paths: list[str] = []
    initializer_owned: list[str] = []
    child_owned: list[str] = []

    if manifest_path.exists():
        try:
            import yaml

            with open(manifest_path, encoding="utf-8") as handle:
                manifest = yaml.safe_load(handle) or {}
            protected_paths = list(manifest.get("protected_files") or [])
            initializer_owned = list(manifest.get("template_directories") or [])
            child_owned = list(manifest.get("project_directories") or [])
        except Exception:
            pass

    dirty = bool(_git(["status", "--porcelain"], root))
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], root) or "unknown"

    return RepositoryProfile(
        repository_id=repo_id,
        root_path=str(root),
        languages=sorted(languages),
        frameworks=sorted(set(frameworks)),
        package_managers=sorted(set(package_managers)),
        test_commands=test_commands,
        build_commands=[],
        ci_workflows=ci_workflows,
        initializer_version=read_template_version(root),
        capability_schema_version=CAPABILITY_SCHEMA_VERSION,
        git_branch=branch,
        git_dirty=dirty,
        protected_paths=protected_paths,
        initializer_owned_paths=initializer_owned,
        child_owned_paths=child_owned,
    )


def write_profile(profile: RepositoryProfile, root: pathlib.Path) -> pathlib.Path:
    out = root / "6_ai_runtime_context" / "REPOSITORY_PROFILE.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
    return out
