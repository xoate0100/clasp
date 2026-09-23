#!/usr/bin/env python3
"""Platform CLI handlers for inspect, plan, doctor, child, release."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(".").resolve()
sys.path.insert(0, str(REPO_ROOT))

from agent_platform.child_registry import child_status, list_children, register_child
from agent_platform.layer3.capability_compiler import compile_plan
from agent_platform.layer3.capability_registry import validate_registry
from agent_platform.layer3.evaluators.registry import evaluators_passed, run_evaluators
from agent_platform.models import ChildRepositoryRecord
from agent_platform.orchestration.workflow import run_inspect_pipeline
from agent_platform.ownership import classify_path, load_manifest
from agent_platform.release import INITIALIZER_VERSION, read_template_version


def cmd_inspect(args: argparse.Namespace) -> int:
    result = run_inspect_pipeline(REPO_ROOT, goal=args.goal or "inspect")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"[inspect] repository_id={result['profile']['repository_id']}")
        print(f"[inspect] initializer_version={result['profile'].get('initializer_version')}")
        print(f"[inspect] evidence_items={result['evidence_count']}")
        print(f"[inspect] disconnects={len(result['model'].get('disconnects', []))}")
        print(f"[inspect] plan_status={result['plan'].get('compilation_status')}")
        print(f"[inspect] outcome={result['run'].get('outcome')}")
    return 0 if result["run"].get("outcome") == "success" else 1


def cmd_plan(args: argparse.Namespace) -> int:
    result = run_inspect_pipeline(REPO_ROOT, goal=args.goal or "plan")
    plan = result["plan"]
    print(json.dumps(plan, indent=2) if args.json else f"[plan] status={plan['compilation_status']} risk={plan['risk_score']}")
    return 0 if plan.get("compilation_status") == "compiled" else 1


def cmd_validate(args: argparse.Namespace) -> int:
    errors = validate_registry(REPO_ROOT)
    results = run_evaluators(REPO_ROOT)
    passed = evaluators_passed(results) and not errors
    if errors:
        print("[validate] capability registry errors:")
        for err in errors:
            print(f"  - {err}")
    for result in results:
        status = "OK" if result.get("passed") else "FAIL"
        print(f"[validate] {result.get('evaluator_id')}: {status}")
    return 0 if passed else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    issues: list[str] = []
    version = read_template_version(REPO_ROOT)
    if version != INITIALIZER_VERSION:
        issues.append(f"manifest version {version} != platform {INITIALIZER_VERSION}")
    issues.extend(validate_registry(REPO_ROOT))
    if not (REPO_ROOT / "agent_platform").is_dir():
        issues.append("agent_platform package missing")
    if issues:
        print("[doctor] issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print("[doctor] OK")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    manifest = load_manifest(REPO_ROOT)
    hub_version = read_template_version(REPO_ROOT)
    print(f"[diff] hub_version={hub_version} platform={INITIALIZER_VERSION}")
    for child in list_children(REPO_ROOT):
        print(
            f"[diff] child={child.get('repository_name')} "
            f"declared={child.get('initializer_version')} "
            f"channel={child.get('release_channel')}"
        )
    return 0


def cmd_child_register(args: argparse.Namespace) -> int:
    record = ChildRepositoryRecord(
        repository_id=args.repository_id or pathlib.Path(args.location).name,
        repository_name=args.name or pathlib.Path(args.location).name,
        repository_location=args.location,
        remote_url=args.remote or "",
        initializer_version=args.initializer_version or "",
    )
    register_child(REPO_ROOT, record)
    print(f"[child] registered {record.repository_id}")
    return 0


def cmd_child_list(_: argparse.Namespace) -> int:
    for child in list_children(REPO_ROOT):
        print(f"{child.get('repository_id')}\t{child.get('repository_name')}\t{child.get('repository_location')}")
    return 0


def cmd_child_status(args: argparse.Namespace) -> int:
    status = child_status(REPO_ROOT, args.repository_id)
    print(json.dumps(status, indent=2))
    return 0 if "error" not in status else 1


def cmd_release(_: argparse.Namespace) -> int:
    print(f"[release] platform version {INITIALIZER_VERSION}")
    print("[release] run: python scripts/check_version_bump.py && pytest && git tag v{version}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="platform_cli.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    inspect = sub.add_parser("inspect")
    inspect.add_argument("--goal", default="inspect")
    inspect.add_argument("--json", action="store_true")

    plan = sub.add_parser("plan")
    plan.add_argument("--goal", default="plan")
    plan.add_argument("--json", action="store_true")

    sub.add_parser("validate")
    sub.add_parser("doctor")
    sub.add_parser("diff")
    sub.add_parser("release")

    child = sub.add_parser("child")
    child_sub = child.add_subparsers(dest="child_cmd", required=True)
    reg = child_sub.add_parser("register")
    reg.add_argument("location")
    reg.add_argument("--repository-id", default="")
    reg.add_argument("--name", default="")
    reg.add_argument("--remote", default="")
    reg.add_argument("--initializer-version", default="")
    child_sub.add_parser("list")
    st = child_sub.add_parser("status")
    st.add_argument("repository_id")

    args = parser.parse_args(argv)

    handlers = {
        "inspect": cmd_inspect,
        "plan": cmd_plan,
        "validate": cmd_validate,
        "doctor": cmd_doctor,
        "diff": cmd_diff,
        "release": cmd_release,
    }
    if args.cmd == "child":
        child_handlers = {
            "register": cmd_child_register,
            "list": cmd_child_list,
            "status": cmd_child_status,
        }
        return child_handlers[args.child_cmd](args)
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
