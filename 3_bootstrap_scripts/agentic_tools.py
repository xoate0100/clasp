#!/usr/bin/env python3
"""
Manage optional in-project agentic tools via feature_flags.yml.

Usage:
    python 3_bootstrap_scripts/agentic_tools.py list
    python 3_bootstrap_scripts/agentic_tools.py enable knowledge_index doc_lifecycle
    python 3_bootstrap_scripts/agentic_tools.py disable reference_validator
    python 3_bootstrap_scripts/agentic_tools.py profile full
    python 3_bootstrap_scripts/agentic_tools.py profile minimal
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agentic.optional_tools import (  # noqa: E402
    TOOL_IDS,
    is_tool_enabled,
    list_tools,
    load_tool_catalog,
    save_optional_tools,
)


def cmd_list(_: argparse.Namespace) -> int:
    for tool in list_tools(REPO_ROOT):
        state = "enabled" if tool["enabled"] else "disabled"
        print(f"- {tool['id']}: {state}")
        if tool.get("description"):
            print(f"    {tool['description'].strip()}")
    return 0


def cmd_enable(args: argparse.Namespace) -> int:
    updates = {tool_id: True for tool_id in args.tools}
    save_optional_tools(updates, REPO_ROOT)
    print(f"[agentic-tools] enabled: {', '.join(args.tools)}")
    return 0


def cmd_disable(args: argparse.Namespace) -> int:
    updates = {tool_id: False for tool_id in args.tools}
    save_optional_tools(updates, REPO_ROOT)
    print(f"[agentic-tools] disabled: {', '.join(args.tools)}")
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    catalog = load_tool_catalog(REPO_ROOT)
    profiles = catalog.get("profiles") or {}
    profile = profiles.get(args.name)
    if not profile:
        print(f"[agentic-tools] FAIL: unknown profile '{args.name}'")
        return 1

    updates: dict[str, bool] = {}
    if profile.get("enable_all"):
        updates = {tool_id: True for tool_id in TOOL_IDS}
    for tool_id in profile.get("disable") or []:
        updates[tool_id] = False
    for tool_id in profile.get("enable") or []:
        updates[tool_id] = True

    save_optional_tools(updates, REPO_ROOT)
    print(f"[agentic-tools] applied profile: {args.name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="agentic_tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List optional tools and status")

    enable = sub.add_parser("enable", help="Enable one or more optional tools")
    enable.add_argument("tools", nargs="+", choices=TOOL_IDS)

    disable = sub.add_parser("disable", help="Disable one or more optional tools")
    disable.add_argument("tools", nargs="+", choices=TOOL_IDS)

    profile = sub.add_parser("profile", help="Apply a tool profile from OPTIONAL_AGENTIC_TOOLS.yaml")
    profile.add_argument("name", choices=["full", "minimal"])

    args = parser.parse_args()
    handlers = {
        "list": cmd_list,
        "enable": cmd_enable,
        "disable": cmd_disable,
        "profile": cmd_profile,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
