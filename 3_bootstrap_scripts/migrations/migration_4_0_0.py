#!/usr/bin/env python3
"""Migration 3.x → 4.0.0: adopt explicit stack adapter selection (default python)."""
from __future__ import annotations

import pathlib
from datetime import datetime, timezone

ROOT = pathlib.Path(".").resolve()
SEL = ROOT / "0_phase0_bootstrap" / "stack_adapter.yaml"
VERSION = ROOT / "0_phase0_bootstrap" / "META_FRAMEWORK_VERSION.yaml"


def ensure_adapter_selection() -> None:
    if SEL.exists():
        text = SEL.read_text(encoding="utf-8")
        if "adapter:" in text:
            print("[migration_4_0_0] stack_adapter.yaml already present")
            return
    SEL.write_text(
        "# Migrated to v4 — explicit adapter selection (zero behavior change)\n"
        "adapter: python\n"
        "manifest: adapters/python/stack_adapter.yaml\n",
        encoding="utf-8",
    )
    print("[migration_4_0_0] wrote adapter: python")


def append_history_note() -> None:
    if not VERSION.exists():
        return
    text = VERSION.read_text(encoding="utf-8")
    if 'to_version: "4.0.0"' in text:
        print("[migration_4_0_0] update_history already has 4.0.0")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = f"""  - from_version: "3.0.0"
    to_version: "4.0.0"
    updated_at: "{stamp}"
    migration_applied: true
    notes: "Stack-agnostic protocol: contract/adapter split; default adapter python"
"""
    # Insert after update_history: line if present, else append
    if "update_history:" in text:
        text = text.replace("update_history:\n", "update_history:\n" + entry, 1)
    else:
        text += "\nupdate_history:\n" + entry
    VERSION.write_text(text, encoding="utf-8")
    print("[migration_4_0_0] appended update_history for 4.0.0")


def main() -> int:
    ensure_adapter_selection()
    append_history_note()
    print("[migration_4_0_0] OK — behavior unchanged for python adapter children")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
