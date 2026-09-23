#!/usr/bin/env python3
"""
Reference validation — unresolved imports and repo path references in Python files.

Checks that third-party imports appear in requirements.txt and that local
import paths resolve to existing modules/files under the repository.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agentic.optional_tools import is_tool_enabled  # noqa: E402

REQUIREMENTS_PATH = REPO_ROOT / "requirements.txt"

REPO_PATH_PREFIXES = (
    "backend/",
    "tests/",
    "docs/",
    "3_bootstrap_scripts/",
    "agentic/",
    "6_ai_runtime_context/",
    "5_reference_architectures/",
    "7_schemas/",
    "0_phase0_bootstrap/",
)

PATH_LIKE = re.compile(r"\.(py|yaml|yml|md|json)$")

DISTRIBUTION_IMPORT_ALIASES = {
    "pyyaml": "yaml",
    "pytest_cov": "pytest_cov",
}


def load_requirements() -> set[str]:
    names: set[str] = set()
    if not REQUIREMENTS_PATH.exists():
        return names
    for line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        token = re.split(r"[<>=!~;\[]", line, maxsplit=1)[0].strip()
        if token:
            names.add(token.lower().replace("-", "_"))
    return names


def local_script_module_exists(file_path: Path, module: str | None) -> bool:
    if not module:
        return False
    top = module.split(".", 1)[0]
    # tests/scripts/** imports hub CLI modules from scripts/ via sys.path
    if "tests" in file_path.parts and "scripts" in file_path.parts:
        scripts_root = REPO_ROOT / "scripts"
        nested_py = scripts_root.joinpath(*module.split(".")).with_suffix(".py")
        nested_init = scripts_root.joinpath(*module.split(".")) / "__init__.py"
        if nested_py.is_file() or nested_init.is_file():
            return True
        top_file = scripts_root / f"{top}.py"
        top_pkg = scripts_root / top / "__init__.py"
        if top_file.is_file() or top_pkg.is_file():
            return True
    if file_path.parent.name == "3_bootstrap_scripts" and "." not in module:
        if (file_path.parent / f"{top}.py").is_file():
            return True
        if (file_path.parent / top / "__init__.py").is_file():
            return True
    if "tests" in file_path.parts:
        if (file_path.parent / f"{top}.py").is_file():
            return True
        script = REPO_ROOT / "3_bootstrap_scripts" / f"{top}.py"
        if script.is_file():
            return True
        migration = REPO_ROOT / "3_bootstrap_scripts" / "migrations" / f"{top}.py"
        if migration.is_file():
            return True
    if module.startswith("modules."):
        rel = module.replace(".", "/") + ".py"
        return (REPO_ROOT / rel).is_file()
    pkg_init = REPO_ROOT / top / "__init__.py"
    if pkg_init.is_file():
        if "." not in module:
            return True
        rel_py = REPO_ROOT / f"{module.replace('.', '/')}.py"
        if rel_py.is_file():
            return True
        rel_pkg = REPO_ROOT / module.replace(".", "/") / "__init__.py"
        if rel_pkg.is_file():
            return True
    if top == "migrations" and file_path.parent.name == "3_bootstrap_scripts":
        return (REPO_ROOT / "3_bootstrap_scripts" / "migrations" / "__init__.py").is_file()
    return False


def requirement_covers(top: str, requirements: set[str]) -> bool:
    if top == "pytest":
        return True
    norm = top.lower().replace("-", "_")
    if norm in requirements:
        return True
    for dist, mod in DISTRIBUTION_IMPORT_ALIASES.items():
        if mod == norm and dist in requirements:
            return True
    return False


def stdlib_modules() -> set[str]:
    if hasattr(sys, "stdlib_module_names"):
        return set(sys.stdlib_module_names)
    return {
        "os", "sys", "pathlib", "json", "re", "subprocess", "typing", "datetime",
        "uuid", "ast", "importlib", "argparse", "collections", "functools", "unittest",
        "math", "hashlib", "dataclasses", "tempfile", "itertools",
    }


def get_target_files() -> tuple[list[Path], bool]:
    if os.environ.get("GUARDRAIL_CI") == "1":
        base_ref = os.environ.get("GUARDRAIL_BASE_REF", "main")
        for cmd in (
            ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
            ["git", "diff", "--name-only", "HEAD~1...HEAD"],
        ):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False, cwd=REPO_ROOT)
                if r.returncode == 0:
                    rels = [p for p in (r.stdout or "").splitlines() if p.strip()]
                    if rels:
                        files = [REPO_ROOT / p for p in rels if p.endswith(".py") and (REPO_ROOT / p).is_file()]
                        return sorted(files), True
            except subprocess.TimeoutExpired:
                continue
    files: list[Path] = []
    for root in (REPO_ROOT / "backend", REPO_ROOT / "agentic", REPO_ROOT / "tests", REPO_ROOT / "3_bootstrap_scripts"):
        if root.is_dir():
            files.extend(root.rglob("*.py"))
    return sorted(files), False


def module_to_path(module: str) -> Path | None:
    parts = module.split(".")
    if parts[0] in ("backend", "agentic", "tests", "scripts"):
        candidate = REPO_ROOT.joinpath(*parts)
        if candidate.with_suffix(".py").is_file():
            return candidate.with_suffix(".py")
        init = candidate / "__init__.py"
        if init.is_file():
            return init
    if module.startswith("3_bootstrap_scripts."):
        rel = module.replace(".", "/") + ".py"
        path = REPO_ROOT / rel
        if path.is_file():
            return path
    return None


def resolve_relative(file_path: Path, module: str | None, level: int) -> str | None:
    if level == 0:
        return module
    parts = list(file_path.relative_to(REPO_ROOT).parts[:-1])
    if level > len(parts):
        return None
    base = parts[: len(parts) - level + 1]
    if module:
        base.extend(module.split("."))
    return ".".join(base)


def check_imports(file_path: Path, requirements: set[str], stdlib: set[str]) -> list[str]:
    errors: list[str] = []
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    except SyntaxError as exc:
        return [f"{file_path}: syntax error: {exc}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0].lower().replace("-", "_")
                if top in stdlib or requirement_covers(top, requirements):
                    continue
                if module_to_path(alias.name):
                    continue
                if local_script_module_exists(file_path, alias.name.split(".")[0]):
                    continue
                errors.append(f"{file_path}: unresolved import '{alias.name}'")
        elif isinstance(node, ast.ImportFrom):
            resolved = resolve_relative(file_path, node.module, node.level)
            if resolved and module_to_path(resolved):
                continue
            top = (resolved or node.module or "").split(".")[0].lower().replace("-", "_")
            if top in stdlib or requirement_covers(top, requirements):
                continue
            if local_script_module_exists(file_path, resolved or node.module):
                continue
            if resolved and module_to_path(resolved):
                continue
            mod_label = resolved or node.module or "relative import"
            errors.append(f"{file_path}: unresolved import from '{mod_label}'")
    return errors


def check_path_literals(file_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    except SyntaxError:
        return errors
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        val = node.value.replace("\\", "/")
        if not PATH_LIKE.search(val):
            continue
        if not any(val.startswith(prefix) for prefix in REPO_PATH_PREFIXES):
            continue
        if not (REPO_ROOT / val).exists():
            errors.append(f"{file_path}: referenced path missing: {val}")
    return errors


def main() -> int:
    if not is_tool_enabled("reference_validator"):
        print("[reference-validate] SKIP: optional tool disabled")
        return 0

    requirements = load_requirements()
    stdlib = stdlib_modules()
    files, check_paths = get_target_files()
    if not files:
        print("[reference-validate] OK: no Python files to scan")
        return 0

    errors: list[str] = []
    for path in files:
        errors.extend(check_imports(path, requirements, stdlib))
        if check_paths:
            errors.extend(check_path_literals(path))

    if errors:
        print("[reference-validate] FAIL: unresolved references:")
        for err in errors[:40]:
            print(f"  - {err}")
        if len(errors) > 40:
            print(f"  ... and {len(errors) - 40} more")
        return 1

    print(f"[reference-validate] OK: checked {len(files)} Python file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
