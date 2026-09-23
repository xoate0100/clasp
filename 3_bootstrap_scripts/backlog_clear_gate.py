#!/usr/bin/env python3
"""Two-key gate for backlog-clear scoped merges (DEC-CP-0013)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.capability_adapter.agent_reviewer import review_major_bump  # noqa: E402


def run_conformance(clone: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "3_bootstrap_scripts/agentic_coordinate_validate.py", "--skip-scan"],
        cwd=str(clone),
        capture_output=True,
        text=True,
    )
    detail = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if proc.returncode != 0:
        return False, detail
    test_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_agentic_registry.py",
            "tests/test_agentic_wiring.py",
            "-q",
            "--tb=line",
        ],
        cwd=str(clone),
        capture_output=True,
        text=True,
        timeout=600,
    )
    test_detail = ((test_proc.stdout or "") + (test_proc.stderr or "")).strip()
    if test_proc.returncode != 0:
        return False, detail + "\n--- pytest ---\n" + test_detail[-2000:]
    factory_extra = clone.name == "Kiwi_Art_Factory"
    if factory_extra:
        gen_proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_generation_agent.py",
                "-q",
                "--tb=line",
            ],
            cwd=str(clone),
            capture_output=True,
            text=True,
            timeout=600,
        )
        gen_detail = ((gen_proc.stdout or "") + (gen_proc.stderr or "")).strip()
        if gen_proc.returncode != 0:
            return False, detail + "\n--- generation ---\n" + gen_detail[-2000:]
    return True, detail + "\npytest: PASS" + ("\ngeneration: PASS" if factory_extra else "")


def run_reviewer(repo: str, diff_summary: str, conformance_ok: bool) -> dict:
    return review_major_bump(
        bump_kind="backlog-clear-remediation",
        changelog=f"Backlog clear remediation for {repo}",
        diff_summary=diff_summary,
        conformance_result="pass" if conformance_ok else "fail",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clone", type=Path, required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--diff-summary", type=Path, required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    diff_text = args.diff_summary.read_text(encoding="utf-8")[:8000]
    conf_ok, conf_detail = run_conformance(args.clone)
    review = run_reviewer(args.repo, diff_text, conf_ok)
    both = conf_ok and review.get("decision") == "approve"
    out = {
        "repo": args.repo,
        "conformance_pass": conf_ok,
        "conformance_detail": conf_detail[-1500:],
        "reviewer_decision": review.get("decision"),
        "reviewer_reason": review.get("reason"),
        "both_keys_pass": both,
    }
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"{args.repo}: conformance={'PASS' if conf_ok else 'FAIL'} reviewer={review.get('decision')}")
        if not both:
            print(conf_detail[-800:])
    return 0 if both else 1


if __name__ == "__main__":
    raise SystemExit(main())
