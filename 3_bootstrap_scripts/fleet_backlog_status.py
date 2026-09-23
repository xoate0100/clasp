#!/usr/bin/env python3
"""Fleet backlog status — surfaces open items for meta status / daemon."""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any, Dict, List

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required", file=sys.stderr)
    sys.exit(1)

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_BACKLOG = ROOT / "docs" / "factory" / "FLEET_BACKLOG.yaml"


def load_backlog(path: pathlib.Path = DEFAULT_BACKLOG) -> Dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "items": []}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {"items": []}


def open_items(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = data.get("items") or []
    return [i for i in items if (i.get("status") or "").lower() == "open"]


def format_status(data: Dict[str, Any]) -> str:
    opens = open_items(data)
    deferred = [
        i for i in (data.get("items") or []) if (i.get("status") or "").lower() == "deferred"
    ]
    lines = [
        f"{len(opens)} open fleet backlog items",
        f"(plus {len(deferred)} deferred)",
        f"source: {DEFAULT_BACKLOG.relative_to(ROOT).as_posix()}",
    ]
    for item in opens:
        rid = item.get("id", "?")
        owner = item.get("proposed_owner", "?")
        pri = item.get("priority", "?")
        daemon = " [daemon-first-test]" if item.get("daemon_first_remediation_test_case") else ""
        lines.append(f"  - {rid} owner={owner} priority={pri}{daemon}")
    return "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show fleet backlog status")
    parser.add_argument("--json", action="store_true", help="Emit open count as JSON")
    parser.add_argument("--path", type=pathlib.Path, default=DEFAULT_BACKLOG)
    args = parser.parse_args(argv)
    data = load_backlog(args.path)
    opens = open_items(data)
    if args.json:
        import json

        print(json.dumps({"open_count": len(opens), "open_ids": [i.get("id") for i in opens]}))
        return 0
    print(format_status(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
