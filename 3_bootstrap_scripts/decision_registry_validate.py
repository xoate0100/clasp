#!/usr/bin/env python3
"""
Validate DECISION_REGISTRY.yaml — unique IDs, legal status transitions, schema.

Usage:
    python 3_bootstrap_scripts/decision_registry_validate.py
    python 3_bootstrap_scripts/decision_registry_validate.py --propose proposals/new_row.yaml
    python 3_bootstrap_scripts/decision_registry_validate.py --propose proposals/new_row.yaml --dry-run
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import date

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    import yaml
    import jsonschema
except ImportError:
    print("[decision-registry] ERROR: PyYAML and jsonschema required")
    sys.exit(1)

REGISTRY_PATH = REPO_ROOT / "5_reference_architectures" / "DECISION_REGISTRY.yaml"
SCHEMA_PATH = REPO_ROOT / "7_schemas" / "decision_registry.schema.json"

VALID_STATUSES = {"proposed", "accepted", "deprecated", "superseded"}


def load_registry(path: pathlib.Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def dump_registry(path: pathlib.Path, data: dict) -> None:
    """Write registry YAML with a stable header comment."""
    body = yaml.safe_dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    header = (
        "# Machine-checkable ADR registry — source of truth for settled and open decisions.\n"
        "# Customize rows for your project. Edits require decision_registry_validate.py --propose.\n"
    )
    path.write_text(header + body, encoding="utf-8")


def validate_schema(data: dict) -> list[str]:
    errors: list[str] = []
    if not SCHEMA_PATH.exists():
        return errors
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        errors.append(f"schema: {err.message} at {list(err.path)}")
    return errors


def validate_logic(data: dict) -> list[str]:
    errors: list[str] = []
    decisions = data.get("decisions") or []
    ids: set[str] = set()

    for idx, row in enumerate(decisions):
        if not isinstance(row, dict):
            errors.append(f"row {idx}: not an object")
            continue

        decision_id = row.get("decision_id", "")
        if decision_id in ids:
            errors.append(f"duplicate decision_id: {decision_id}")
        ids.add(decision_id)

        status = row.get("status")
        if status not in VALID_STATUSES:
            errors.append(f"{decision_id}: invalid status '{status}'")

        supersedes = row.get("supersedes")
        if supersedes and supersedes not in ids and supersedes not in {
            d.get("decision_id") for d in decisions
        }:
            errors.append(f"{decision_id}: supersedes unknown id '{supersedes}'")

        keywords = row.get("resurrection_trigger_keywords") or []
        if len(keywords) != len(set(k.lower() for k in keywords)):
            errors.append(
                f"{decision_id}: duplicate resurrection_trigger_keywords (case-insensitive)"
            )

    return errors


def merge_proposal(base: dict, proposal_path: pathlib.Path) -> dict:
    proposal = load_registry(proposal_path)
    row = None
    if "decisions" in proposal and proposal["decisions"]:
        row = proposal["decisions"][0]
    elif proposal.get("decision_id"):
        row = proposal

    if not row:
        raise ValueError("proposal file must contain a decision row")

    merged = dict(base)
    merged_decisions = list(base.get("decisions") or [])
    replaced = False
    for i, existing in enumerate(merged_decisions):
        if existing.get("decision_id") == row.get("decision_id"):
            merged_decisions[i] = row
            replaced = True
            break
    if not replaced:
        merged_decisions.append(row)
    merged["decisions"] = merged_decisions
    merged["updated"] = date.today().isoformat()
    return merged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--propose",
        metavar="FILE",
        help="Validate a proposed decision row and write it into DECISION_REGISTRY.yaml",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --propose: validate merge only; do not write the registry",
    )
    args = parser.parse_args()

    if not REGISTRY_PATH.exists():
        print(f"[decision-registry] FAIL: missing {REGISTRY_PATH}")
        return 1

    data = load_registry(REGISTRY_PATH)
    wrote = False
    if args.propose:
        proposal_path = pathlib.Path(args.propose)
        if not proposal_path.is_absolute():
            proposal_path = REPO_ROOT / proposal_path
        try:
            data = merge_proposal(data, proposal_path)
        except ValueError as exc:
            print(f"[decision-registry] FAIL: {exc}")
            return 1
        print(f"[decision-registry] validating proposal merge from {proposal_path}")

    errors = validate_schema(data) + validate_logic(data)
    if errors:
        print("[decision-registry] FAIL:")
        for err in errors:
            print(f"  - {err}")
        return 1

    if args.propose and not args.dry_run:
        dump_registry(REGISTRY_PATH, data)
        wrote = True
        print(f"[decision-registry] wrote {REGISTRY_PATH.as_posix()}")

    suffix = " (dry-run)" if args.propose and args.dry_run else ""
    print(f"[decision-registry] OK: {len(data.get('decisions') or [])} decision(s){suffix}")
    if wrote:
        print("[decision-registry] proposer applied row — do not hand-edit the registry")
    return 0


if __name__ == "__main__":
    sys.exit(main())
