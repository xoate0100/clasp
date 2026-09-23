#!/usr/bin/env python3
"""Validate a factory-run-manifest/v1 document (incl. agent-driven blog runs)."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / "7_schemas" / "factory_run" / "run_manifest.schema.json"

try:
    import jsonschema
except ImportError:
    print("[manifest_validate] ERROR: jsonschema required", file=sys.stderr)
    sys.exit(1)


def validate_manifest(doc: dict) -> list[str]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    return [
        f"{list(err.path)}: {err.message}"
        for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate factory-run-manifest/v1")
    parser.add_argument("manifest", type=pathlib.Path)
    args = parser.parse_args(argv)
    doc = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors = validate_manifest(doc)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
