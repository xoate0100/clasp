#!/usr/bin/env python3
"""Governance gap registry status — surfaces open gaps for meta status."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "docs" / "factory" / "GOVERNANCE_GAP_REGISTRY.yaml"


def load_registry(path: pathlib.Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "items": []}
    if yaml is None:
        print("ERROR: PyYAML required", file=sys.stderr)
        sys.exit(1)
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {"items": []}


def open_gaps(data: dict[str, Any]) -> list[dict[str, Any]]:
    items = data.get("items") or []
    return [i for i in items if (i.get("status") or "").lower() == "open"]


def format_status(data: dict[str, Any]) -> str:
    items = data.get("items") or []
    opens = open_gaps(data)
    gated = [i for i in items if (i.get("status") or "").lower() == "gated"]
    judgment = [i for i in items if (i.get("classification") or "") == "judgment-call"]
    lines = [
        f"{len(opens)} open governance gaps",
        f"({len(gated)} gated, {len(judgment)} judgment-call total)",
        f"source: {DEFAULT_REGISTRY.relative_to(ROOT).as_posix()}",
    ]
    for item in opens[:12]:
        lines.append(f"  - {item.get('id', '?')} [{item.get('classification', '?')}] {item.get('title', '')[:60]}")
    if len(opens) > 12:
        lines.append(f"  ... +{len(opens) - 12} more")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show governance gap registry status")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--path", type=pathlib.Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args(argv)
    data = load_registry(args.path)
    opens = open_gaps(data)
    if args.json:
        print(json.dumps({"open_count": len(opens), "open_ids": [i.get("id") for i in opens]}))
        return 0
    print(format_status(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
