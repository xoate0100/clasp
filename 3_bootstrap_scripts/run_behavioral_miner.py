#!/usr/bin/env python3
"""Run the behavioral daemon miner (Wave F Half 1)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.behavioral_daemon.miner import BehavioralMiner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Behavioral daemon miner — ingest, reconcile, propose")
    parser.add_argument("--dry-run", action="store_true", help="Do not append proposals to sink")
    parser.add_argument("--no-emit", action="store_true", help="Skip proposal emission")
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    args = parser.parse_args()

    miner = BehavioralMiner(ROOT)
    result = miner.run(emit=not args.no_emit, dry_run=args.dry_run)

    summary = {
        "sink_events": result.ingest.count,
        "sink_rejected": len(result.ingest.rejected),
        "derived_clusters": result.derived_counts,
        "reconcile_agreements": result.reconcile_agreements,
        "reconcile_disagreements": result.reconcile_disagreements,
        "repeated_tools": [d.to_dict() for d in result.repeated],
        "proposals": len(result.proposals),
        "gate": {
            "passed": result.gate.passed,
            "reasons": result.gate.reasons,
            "reproduced": result.gate.reproduced,
            "missing": result.gate.missing,
        },
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(result.gate.summary())
        print(f"sink: {result.ingest.count} events, {len(result.ingest.rejected)} rejected")
        print(f"reconcile: {result.reconcile_agreements} agreements, {result.reconcile_disagreements} disagreements")
        print(f"proposals: {len(result.proposals)} ({len(result.emit_results)} emitted)")
        for det in result.repeated[:8]:
            print(f"  {det.capability} ×{det.count} — {', '.join(det.evidence_repos[:4])}…")

    return 0 if result.gate.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
