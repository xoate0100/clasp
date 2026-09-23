#!/usr/bin/env python3
"""Fleet-wide governance plumbing audit (API-based, no full clones)."""
from __future__ import annotations

import base64
import json
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

HUB = pathlib.Path(__file__).resolve().parents[1]
OUT = HUB / "docs" / "factory" / "PLUMBING_AUDIT_INVENTORY.md"
JSON_OUT = HUB / "_recon_scratch" / "plumbing_scan" / "inventory.json"
ORG = "xoate0100"
SCOPE_MARKERS = ("hub_task_gates_apply", "_hub_gates_apply", "governance_scope")
HUB_GATE_PATHS = (
    "3_bootstrap_scripts/task_completion_gate.py",
    "3_bootstrap_scripts/guardrail_enforcement.py",
    "3_bootstrap_scripts/check_state_transition.py",
    "scripts/check_version_bump.py",
)


def gh_json(args: list[str]) -> object:
    out = subprocess.check_output(["gh"] + args, text=True)
    return json.loads(out)


def gh_raw(args: list[str]) -> str:
    return subprocess.check_output(["gh"] + args, text=True).strip()


def gh_file_content(repo: str, path: str) -> str | None:
    try:
        data = gh_raw(["api", f"repos/{ORG}/{repo}/contents/{path}", "-q", ".content"])
        if not data:
            return None
        return base64.b64decode(data).decode("utf-8", errors="replace")
    except subprocess.CalledProcessError:
        return None


def list_repos() -> list[str]:
    rows = gh_json(["repo", "list", ORG, "--limit", "200", "--json", "name,isArchived"])
    return sorted(r["name"] for r in rows if not r.get("isArchived"))


def scan_repo(name: str) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    is_hub = name == "project_initializer"

    for path in HUB_GATE_PATHS:
        text = gh_file_content(name, path)
        if text is None:
            continue
        if not any(m in text for m in SCOPE_MARKERS):
            hits.setdefault("P1_hub_gate_no_scope", []).append(path)

    gs = gh_file_content(name, "3_bootstrap_scripts/governance_scope.py")
    pcc = gh_file_content(name, ".pre-commit-config.yaml")
    gate_text = gh_file_content(name, "3_bootstrap_scripts/task_completion_gate.py") or ""
    guard_text = gh_file_content(name, "3_bootstrap_scripts/guardrail_enforcement.py") or ""
    has_scope_import = any(
        m in gate_text or m in guard_text
        for m in ("governance_scope", "hub_task_gates_apply", "_hub_gates_apply")
    )
    if pcc and ("task_completion_gate" in pcc or "guardrail-enforcement" in pcc):
        if gs is None and not has_scope_import:
            hits.setdefault("P4_hook_hub_paths", []).append(
                ".pre-commit-config.yaml without governance_scope (file or import)"
            )

    ff = gh_file_content(name, "0_phase0_bootstrap/feature_flags.yml")
    if ff:
        if re.search(r"enforcement:\s*off", ff, re.I):
            hits.setdefault("P3_P6_enforcement_flags", []).append("enforcement: off")
        if re.search(r"agentic:\s*\n\s*enabled:\s*false", ff, re.I):
            hits.setdefault("P3_P6_enforcement_flags", []).append("agentic.enabled: false")

    if is_hub:
        hits.pop("P1_hub_gate_no_scope", None)  # hub has scope after task 2

    return hits


def search_no_verify() -> dict[str, list[str]]:
    """Org-wide code search for bypass flags in scripts/workflows."""
    by_repo: dict[str, list[str]] = {}
    queries = [
        f"org:{ORG} --no-verify",
        f"org:{ORG} --no-gpg-sign",
    ]
    seen: set[tuple[str, str]] = set()
    for q in queries:
        try:
            rows = gh_json(["search", "code", q, "--json", "path,repository,textMatches", "--limit", "100"])
        except subprocess.CalledProcessError:
            continue
        for row in rows:
            repo = row.get("repository", {}).get("name", "")
            path = row.get("path", "")
            if not repo or not path:
                continue
            if "DRIFT_VECTORS" in path or "PLUMBING_CLASS" in path:
                continue
            if path.endswith((".md",)) and "do not use" in str(row).lower():
                continue
            key = (repo, path)
            if key in seen:
                continue
            seen.add(key)
            by_repo.setdefault(repo, []).append(f"P2_no_verify_ref: {path}")
    return by_repo


def render(all_findings: dict[str, dict[str, list[str]]], repo_count: int) -> str:
    pattern_counts: dict[str, int] = {}
    for patterns in all_findings.values():
        for p in patterns:
            pattern_counts[p] = pattern_counts.get(p, 0) + 1

    lines = [
        "# Governance Plumbing Audit Inventory",
        "",
        "**Plan:** governance-plumbing-audit task 3",
        f"**Repos scanned:** {repo_count}",
        f"**Repos with findings:** {sum(1 for v in all_findings.values() if v)}",
        "",
        "## Pattern summary",
        "",
        "| Pattern | Repos |",
        "|---|---|",
    ]
    for p in sorted(pattern_counts):
        lines.append(f"| {p} | {pattern_counts[p]} |")
    lines.extend(["", "## Per-repo findings", ""])
    for repo in sorted(all_findings):
        patterns = all_findings[repo]
        if not patterns:
            continue
        lines.append(f"### {repo}")
        for p, details in sorted(patterns.items()):
            lines.append(f"- **{p}**")
            for d in details[:8]:
                lines.append(f"  - `{d}`")
            if len(details) > 8:
                lines.append(f"  - ... +{len(details) - 8} more")
        lines.append("")

    clean = [r for r, p in all_findings.items() if not p]
    lines.append(f"## Clean ({len(clean)} repos)")
    lines.append("")
    if clean:
        lines.append(", ".join(clean[:40]) + (" ..." if len(clean) > 40 else ""))
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    repos = list_repos()
    print(f"[plumbing-scan] {len(repos)} repos", flush=True)
    findings: dict[str, dict[str, list[str]]] = {}

    for i, name in enumerate(repos, 1):
        print(f"  [{i}/{len(repos)}] {name}", flush=True)
        findings[name] = scan_repo(name)

    print("[plumbing-scan] searching org for bypass refs...", flush=True)
    bypass = search_no_verify()
    for repo, items in bypass.items():
        for item in items:
            pat, detail = item.split(": ", 1)
            findings.setdefault(repo, {}).setdefault(pat, []).append(detail)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(findings, len(repos)), encoding="utf-8")
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(f"[plumbing-scan] wrote {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
