#!/usr/bin/env python3
"""Validate syntax for staged Python, JSON, and YAML files."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from pre_commit_utils import MAX_FILE_SIZE, files_from_argv_or_staged, norm_path  # noqa: E402

try:
    import yaml
except ImportError:
    yaml = None


def validate_python(path: Path) -> str | None:
    try:
        ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return f"{path}: Python syntax error at line {exc.lineno}: {exc.msg}"
    except OSError as exc:
        return f"{path}: {exc}"
    return None


def validate_json(path: Path) -> str | None:
    try:
        json.load(path.open(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return f"{path}: JSON error at line {exc.lineno}: {exc.msg}"
    except OSError as exc:
        return f"{path}: {exc}"
    return None


def validate_yaml(path: Path) -> str | None:
    if yaml is None:
        return None
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return f"{path}: YAML error: {exc}"
    except OSError as exc:
        return f"{path}: {exc}"
    return None


def main() -> int:
    errors: list[str] = []
    for file_path in files_from_argv_or_staged(sys.argv):
        path = Path(file_path)
        if not path.is_file():
            continue
        if path.stat().st_size > MAX_FILE_SIZE:
            continue

        fwd = norm_path(file_path)
        if fwd.endswith(".py"):
            err = validate_python(path)
        elif fwd.endswith(".json"):
            err = validate_json(path)
        elif fwd.endswith((".yaml", ".yml")):
            err = validate_yaml(path)
        else:
            continue
        if err:
            errors.append(err)

    if errors:
        print("[validate-syntax] FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("[validate-syntax] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
