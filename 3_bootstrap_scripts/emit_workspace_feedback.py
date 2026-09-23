#!/usr/bin/env python3
"""
Emit a workspace.feedback event (CI / scheduled). Automatic pipe — not a human script ritual.

Writes to the durable sink (WORKSPACE_FEEDBACK_SINK or default digest path).
Optionally repository_dispatch's the hub ingest workflow when HUB_FEEDBACK_TOKEN is set.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from workspace_feedback_sink import append_event, default_sink_path  # noqa: E402


def detect_spoke_id() -> str:
    env = os.environ.get("WORKSPACE_FEEDBACK_SPOKE_ID")
    if env:
        return env
    try:
        remote = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            text=True,
            timeout=10,
            cwd=str(ROOT),
        ).strip()
        # https://github.com/owner/repo.git or git@github.com:owner/repo.git
        import re

        m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", remote)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
    except Exception:
        pass
    return "unknown/spoke"


def template_version() -> Optional[str]:
    manifest = ROOT / "0_phase0_bootstrap" / "META_FRAMEWORK_VERSION.yaml"
    if not manifest.exists():
        return None
    try:
        import yaml

        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        return data.get("template_version")
    except Exception:
        return None


def build_heartbeat_event(spoke_id: str, kind: str, note: str) -> Dict[str, Any]:
    return {
        "spoke_id": spoke_id,
        "kind": kind,
        "payload": {
            "note": note,
            "template_version": template_version(),
            "emitted_by": "emit_workspace_feedback.py",
            "ci": bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS")),
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "ref": os.environ.get("GITHUB_REF"),
        },
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "labels": ["workspace-feedback", "auto-emit"],
    }


def maybe_dispatch_hub(record: Dict[str, Any]) -> Optional[str]:
    """Push the same event upstream via repository_dispatch when token present."""
    token = os.environ.get("HUB_FEEDBACK_TOKEN") or os.environ.get("GH_TOKEN")
    hub = os.environ.get("HUB_FEEDBACK_REPO", "xoate0100/project_initializer")
    if not token:
        return None
    # Only cross-dispatch when this is not already the hub repo writing locally.
    spoke = record.get("spoke_id", "")
    if spoke.endswith("/project_initializer") and "HUB_FEEDBACK_TOKEN" not in os.environ:
        return "skipped-hub-local"
    body = {
        "event_type": "workspace.feedback",
        "client_payload": {"record": record},
    }
    import urllib.request

    req = urllib.request.Request(
        f"https://api.github.com/repos/{hub}/dispatches",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return f"dispatched:{resp.status}"
    except Exception as exc:
        return f"dispatch-failed:{exc}"


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Emit workspace.feedback event to durable sink")
    parser.add_argument("--spoke-id", default=None)
    parser.add_argument("--kind", default="PATTERN_DETECTED")
    parser.add_argument("--note", default="Automatic workspace.feedback heartbeat")
    parser.add_argument("--sink-path", type=pathlib.Path, default=None)
    parser.add_argument("--event-json", type=pathlib.Path, default=None, help="Raw event JSON file")
    parser.add_argument("--source-path", default="emit")
    parser.add_argument("--no-dispatch", action="store_true")
    args = parser.parse_args(argv)

    if args.event_json:
        event = json.loads(args.event_json.read_text(encoding="utf-8"))
    else:
        spoke = args.spoke_id or detect_spoke_id()
        event = build_heartbeat_event(spoke, args.kind, args.note)

    sink = args.sink_path or default_sink_path(ROOT)
    result = append_event(event, sink_path=sink, source_path=args.source_path, project_root=ROOT)
    if not result.get("accepted"):
        print(json.dumps(result, indent=2))
        return 1
    dispatch = None if args.no_dispatch else maybe_dispatch_hub(result["record"])
    out = {
        "accepted": True,
        "reached_sink": True,
        "sink": result["sink"],
        "event_id": result["event_id"],
        "dispatch": dispatch,
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
