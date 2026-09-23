#!/usr/bin/env python3
"""Run the behavioral daemon remediation agent (Wave F Half 2)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.behavioral_daemon.flags import load_behavioral_daemon_flags  # noqa: E402
from backend.behavioral_daemon.remediation_agent import RemediationAgent  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Behavioral daemon remediation — propose-only Kiwi fixes")
    parser.add_argument(
        "--scratch",
        type=Path,
        default=ROOT / "_recon_scratch" / "wave_f_kiwi",
        help="Directory containing Kiwi_* clones",
    )
    parser.add_argument("--dry-run", action="store_true", help="Apply patches locally only; do not open PRs")
    parser.add_argument("--open-prs", action="store_true", help="Push branches and open propose-only PRs")
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    parser.add_argument(
        "--write-proposal",
        type=Path,
        default=ROOT / "docs" / "factory" / "WAVE_F_KIWI_PROPOSAL.md",
    )
    args = parser.parse_args()

    flags = load_behavioral_daemon_flags(ROOT)
    agent = RemediationAgent(ROOT, flags=flags)
    result = agent.propose_kiwi_cluster(
        args.scratch,
        dry_run=args.dry_run or not args.open_prs,
        open_prs=args.open_prs and not args.dry_run,
    )
    agent.write_proposal_doc(result, args.write_proposal)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"flags: remediation={flags.remediation_enabled} auto_fix={flags.auto_fix_enabled} "
              f"auto_merge={flags.auto_merge_enabled} auto_promote={flags.auto_promote_enabled}")
        if result.blocked_reason:
            print(f"BLOCKED: {result.blocked_reason}")
        for p in result.proposals:
            status = "PASS" if p.validate_ok else "FAIL"
            pr = p.pr_url or "(no PR)"
            print(f"{p.repo}: validate={status} reviewer={p.reviewer.get('decision')} pr={pr}")
            if p.error:
                print(f"  error: {p.error}")
        print(f"proposal doc: {args.write_proposal}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
