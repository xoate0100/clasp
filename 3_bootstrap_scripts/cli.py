#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys


def _python() -> str:
    return sys.executable


def _run(cmd: list[str], env: dict | None = None) -> int:
    return subprocess.call(cmd, env=env)


def _run_validate() -> int:
    """
    Run pre-commit across the tree.

    Tree-mutating autofixers (trailing-whitespace, end-of-file-fixer) are SKIP'd
    during validate so --all-files does not dirty hundreds of unrelated files and
    trip GATE-4. Commit-time hooks still enforce them.

    Remaining hooks that rewrite (e.g. docs-sync) may still exit 1 on first pass;
    re-run once for VALIDATE_AUTOFIXER_STABILITY.
    """
    env = os.environ.copy()
    skip_hooks = "trailing-whitespace,end-of-file-fixer"
    existing = (env.get("SKIP") or "").strip()
    env["SKIP"] = f"{existing},{skip_hooks}" if existing else skip_hooks
    cmd = ["pre-commit", "run", "--all-files"]
    first = _run(cmd, env=env)
    if first == 0:
        return 0
    print("[cli] validate: re-running pre-commit after autofixer modifications...")
    return _run(cmd, env=env)


def _py_cmd(*args: str) -> list[str]:
    """Invoke a script with the current interpreter (Windows-safe; no hardcoded python3)."""
    return [_python(), *args]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="cli.py",
        description=(
            "Python reference adapter CLI. Prefer the neutral dispatcher "
            "(meta.ps1 / meta.sh) which routes via adapters/<id>/stack_adapter.json."
        ),
    )
    sub = ap.add_subparsers(dest="cmd")

    init = sub.add_parser("init", help="Initialize project from MVP_SPECIFICATION.yaml")
    init.add_argument("--guided", action="store_true", help="Run guided wizard to generate/refresh PROJECT_LAYOUT before init.")
    init.add_argument("--answers", default="", help="Wizard answers YAML (declarative).")
    init.add_argument("--preset", default="", help="Wizard preset override (e.g., nextjs_root, apps_packages, template_canonical).")
    init.add_argument("--mode", default="", help="Wizard adaptation mode override (adopt_existing|normalize_to_template).")
    init.add_argument("--auto-apply", action="store_true", help="Wizard: set PROJECT_LAYOUT.adaptation.auto_apply=true")

    sub.add_parser("generate-context", help="Generate AI execution context document")
    # Neutral verb aliases (COMMAND_INTERFACE.md)
    sub.add_parser("check-updates", help="Alias: check for template updates (neutral verb)")
    apply_updates = sub.add_parser("apply-updates", help="Alias: apply template updates (neutral verb)")
    apply_updates.add_argument("--template-repo", default="", help="Template repository URL")
    apply_updates.add_argument("--version", default="", help="Specific version to update to")
    apply_updates.add_argument("--force", action="store_true", help="Force update even if versions match")
    apply_updates.add_argument("--dry-run", action="store_true", help="Show what would be updated without applying")
    apply_updates.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    update = sub.add_parser("update-template", help="Update template files from template repository")
    update.add_argument("--template-repo", default="", help="Template repository URL")
    update.add_argument("--version", default="", help="Specific version to update to")
    update.add_argument("--dry-run", action="store_true", help="Show what would be updated")
    update.add_argument("--init-versioning", action="store_true", help="Initialize versioning for pre-versioned projects")
    update.add_argument("--force", action="store_true", help="Force update even if versions match")
    update.add_argument("--no-backup", action="store_true", help="Skip backup creation (not recommended)")

    verify = sub.add_parser("verify-template", help="Verify template file integrity")
    verify.add_argument("--template-repo", default="", help="Template repository URL")
    verify.add_argument("--version", default="", help="Specific version to verify against")

    status = sub.add_parser("template-status", help="Show current template version and update status")
    status.add_argument("--template-repo", default="", help="Template repository URL")
    feedback = sub.add_parser("submit-feedback", help="Submit AI feedback to template repository")
    feedback.add_argument("--dry-run", action="store_true", help="Show what would be submitted")
    feedback.add_argument("--github-token", default="", help="GitHub token (or set GITHUB_TOKEN env var)")
    upgrade = sub.add_parser("upgrade-legacy", help="Upgrade legacy project to project_initializer format")
    upgrade.add_argument("--analyze", action="store_true", help="Phase 1: Analyze project structure")
    upgrade.add_argument("--plan", action="store_true", help="Phase 2: Generate upgrade plan")
    upgrade.add_argument("--execute", action="store_true", help="Phase 3: Execute upgrade plan")
    upgrade.add_argument("--validate", action="store_true", help="Phase 4: Validate upgrade")
    upgrade.add_argument("--template-repo", default="", help="Template repository URL")
    migrate_v0 = sub.add_parser("migrate-v0", help="Migrate v0.dev project to project_initializer structure")
    migrate_v0.add_argument("project_path", nargs="?", default=".", help="Path to v0 project (default: current directory)")
    migrate_v0.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    migrate_v0.add_argument("--force", action="store_true", help="Force migration even if project_initializer structure exists")
    sub.add_parser("validate", help="Run all pre-commit hooks")
    health = sub.add_parser("health", help="Validate agentic toolchain health")
    health.add_argument("--run-tests", action="store_true", help="Execute pytest suite")
    health.add_argument("--json", dest="json_out", default="", help="Write JSON health report")
    sub.add_parser("status", help="Show fleet backlog status (open item count)")
    crosswalk = sub.add_parser("crosswalk", help="Onboard/upgrade against the hub (neutral verb)")
    crosswalk.add_argument("--adapter", default="", help="Force adapter id")
    crosswalk.add_argument("--dry-run", action="store_true")
    crosswalk.add_argument("--offline", action="store_true")
    crosswalk.add_argument("--force", action="store_true")
    onboard = sub.add_parser("onboard", help="Alias: crosswalk")
    onboard.add_argument("--adapter", default="", help="Force adapter id")
    onboard.add_argument("--dry-run", action="store_true")
    onboard.add_argument("--offline", action="store_true")
    onboard.add_argument("--force", action="store_true")
    autofix = sub.add_parser("auto-fix", help="Run feedback issue analysis and fix generation pipeline")
    autofix.add_argument("--owner", default="", help="GitHub repo owner (default: from git remote)")
    autofix.add_argument("--repo", default="", help="GitHub repo name (default: from git remote)")
    autofix.add_argument("--token", default="", help="GitHub token (or GITHUB_TOKEN env var)")
    sub.add_parser("trace", help="Generate traceability graph")
    sub.add_parser("review", help="Run AI review")
    sub.add_parser("commit-checkpoint", help="Commit with validation and proper message format")

    agentic = sub.add_parser("agentic", help="Agentic coordination commands")
    agentic_sub = agentic.add_subparsers(dest="agentic_cmd", required=True)
    agentic_sub.add_parser("session-start", help="Regenerate context and run phase gate status")
    agentic_sub.add_parser("pre-commit-review", help="Run reviewer pipeline on staged changes")
    agentic_sub.add_parser("validate", help="Run all agentic registry validators")

    tools = agentic_sub.add_parser("tools", help="Manage optional in-project agentic tools")
    tools_sub = tools.add_subparsers(dest="tools_cmd", required=True)
    tools_sub.add_parser("list", help="List optional tools and enabled status")
    enable = tools_sub.add_parser("enable", help="Enable optional tools")
    enable.add_argument("tool_ids", nargs="+")
    disable = tools_sub.add_parser("disable", help="Disable optional tools")
    disable.add_argument("tool_ids", nargs="+")
    profile = tools_sub.add_parser("profile", help="Apply full or minimal tool profile")
    profile.add_argument("name", choices=["full", "minimal"])

    inspect = sub.add_parser("inspect", help="Scan repository and run Layer 0-3 inspect pipeline")
    inspect.add_argument("--goal", default="inspect")
    inspect.add_argument("--json", action="store_true")
    plan = sub.add_parser("plan", help="Compile capability plan (dry-run)")
    plan.add_argument("--goal", default="plan")
    plan.add_argument("--json", action="store_true")
    sub.add_parser("doctor", help="Diagnose platform installation and registry health")
    sub.add_parser("diff", help="Compare hub vs child repository versions")
    sub.add_parser("release", help="Show release preparation guidance")
    validate_platform = sub.add_parser("validate-platform", help="Validate platform registries and connectivity")
    child = sub.add_parser("child", help="Child repository registry")
    child_sub = child.add_subparsers(dest="child_cmd")
    child_reg = child_sub.add_parser("register", help="Register a child repository")
    child_reg.add_argument("location")
    child_reg.add_argument("--repository-id", default="")
    child_reg.add_argument("--name", default="")
    child_reg.add_argument("--remote", default="")
    child_reg.add_argument("--initializer-version", default="")
    child_sub.add_parser("list", help="List registered child repositories")
    child_status = child_sub.add_parser("status", help="Child repository status")
    child_status.add_argument("repository_id")

    args = ap.parse_args(argv)

    if args.cmd == "init":
        if getattr(args, "guided", False):
            cmd = _py_cmd("3_bootstrap_scripts/init_wizard.py", "--non_interactive")
            if args.answers:
                cmd += ["--answers", args.answers]
            if args.preset:
                cmd += ["--preset", args.preset]
            if args.mode:
                cmd += ["--mode", args.mode]
            if getattr(args, "auto_apply", False):
                cmd += ["--auto_apply"]
            rc = _run(cmd)
            if rc != 0:
                return rc
        return _run(_py_cmd("3_bootstrap_scripts/init_project.py"))

    if args.cmd == "generate-context":
        return _run(_py_cmd("3_bootstrap_scripts/generate_ai_context.py"))
    if args.cmd in ("update-template", "apply-updates"):
        cmd = _py_cmd("3_bootstrap_scripts/template_update.py")
        if getattr(args, "template_repo", ""):
            cmd.extend(["--template-repo", args.template_repo])
        if getattr(args, "version", ""):
            cmd.extend(["--version", args.version])
        if getattr(args, "dry_run", False):
            cmd.append("--dry-run")
        if getattr(args, "init_versioning", False):
            cmd.append("--init-versioning")
        if getattr(args, "force", False):
            cmd.append("--force")
        if getattr(args, "no_backup", False):
            cmd.append("--no-backup")
        return _run(cmd)
    if args.cmd == "verify-template":
        cmd = _py_cmd("3_bootstrap_scripts/template_update.py", "--verify-only")
        if getattr(args, "template_repo", ""):
            cmd.extend(["--template-repo", args.template_repo])
        if getattr(args, "version", ""):
            cmd.extend(["--version", args.version])
        return _run(cmd)
    if args.cmd in ("template-status", "check-updates"):
        cmd = _py_cmd("3_bootstrap_scripts/template_update.py", "--status")
        if getattr(args, "template_repo", ""):
            cmd.extend(["--template-repo", args.template_repo])
        return _run(cmd)
    if args.cmd == "submit-feedback":
        cmd = _py_cmd("3_bootstrap_scripts/feedback_collector.py")
        if getattr(args, "dry_run", False):
            cmd.append("--dry-run")
        if getattr(args, "github_token", ""):
            cmd.extend(["--github-token", args.github_token])
        return _run(cmd)
    if args.cmd == "upgrade-legacy":
        cmd = _py_cmd("3_bootstrap_scripts/upgrade_legacy_project.py")
        if getattr(args, "analyze", False):
            cmd.append("--analyze")
        if getattr(args, "plan", False):
            cmd.append("--plan")
        if getattr(args, "execute", False):
            cmd.append("--execute")
        if getattr(args, "validate", False):
            cmd.append("--validate")
        if getattr(args, "template_repo", ""):
            cmd.extend(["--template-repo", args.template_repo])
        return _run(cmd)
    if args.cmd == "migrate-v0":
        cmd = _py_cmd("3_bootstrap_scripts/migrate_v0_to_initializer.py")
        project_path = getattr(args, "project_path", ".")
        if project_path:
            cmd.append(project_path)
        if getattr(args, "dry_run", False):
            cmd.append("--dry-run")
        if getattr(args, "force", False):
            cmd.append("--force")
        return _run(cmd)
    if args.cmd == "validate":
        return _run_validate()
    if args.cmd == "health":
        cmd = [_python(), "scripts/validate_agentic_capabilities.py"]
        if getattr(args, "run_tests", False):
            cmd.append("--run-tests")
        if getattr(args, "json_out", ""):
            cmd.extend(["--json", args.json_out])
        return _run(cmd)
    if args.cmd == "status":
        rc = _run(_py_cmd("3_bootstrap_scripts/fleet_backlog_status.py"))
        print()
        rc2 = _run(_py_cmd("3_bootstrap_scripts/governance_gap_status.py"))
        return rc if rc else rc2
    if args.cmd in ("crosswalk", "onboard"):
        cmd = _py_cmd("3_bootstrap_scripts/crosswalk.py")
        if getattr(args, "adapter", ""):
            cmd.extend(["--adapter", args.adapter])
        if getattr(args, "dry_run", False):
            cmd.append("--dry-run")
        if getattr(args, "offline", False):
            cmd.append("--offline")
        if getattr(args, "force", False):
            cmd.append("--force")
        return _run(cmd)
    if args.cmd == "auto-fix":
        token = getattr(args, "token", "") or os.environ.get("GITHUB_TOKEN", "")
        owner = getattr(args, "owner", "")
        repo = getattr(args, "repo", "")
        if not owner or not repo:
            try:
                remote = subprocess.check_output(
                    ["git", "remote", "get-url", "origin"], text=True
                ).strip()
                # https://github.com/owner/repo.git or git@github.com:owner/repo.git
                import re
                match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", remote)
                if match:
                    owner = owner or match.group(1)
                    repo = repo or match.group(2)
            except subprocess.CalledProcessError:
                pass
        if not owner or not repo:
            print("ERROR: Could not determine GitHub owner/repo. Use --owner and --repo.")
            return 1
        if not token:
            print("ERROR: GITHUB_TOKEN required for auto-fix pipeline.")
            return 1
        steps = [
            [_python(), "scripts/fetch_child_feedback_issues.py",
             "--owner", owner, "--repo", repo, "--token", token,
             "--output", "data/issue_analysis.json"],
            [_python(), "scripts/analyze_feedback_patterns.py",
             "--input", "data/issue_analysis.json",
             "--output", "data/pattern_analysis.json"],
            [_python(), "scripts/prioritize_fixes.py",
             "--input", "data/pattern_analysis.json",
             "--output", "data/prioritized_queue.json"],
            [_python(), "scripts/generate_fixes.py",
             "--input", "data/prioritized_queue.json",
             "--output-dir", "data/generated_fixes"],
            [_python(), "scripts/validate_fixes.py",
             "--input", "data/generated_fixes/generated_fixes.json",
             "--output", "data/validation_report.json"],
        ]
        for step in steps:
            rc = _run(step)
            if rc != 0:
                return rc
        print("Auto-fix pipeline complete. Review data/generated_fixes/ and data/validation_report.json")
        return 0
    if args.cmd == "trace":
        return _run(_py_cmd("3_bootstrap_scripts/traceability_graph.py"))
    if args.cmd == "review":
        return _run(_py_cmd("3_bootstrap_scripts/ai_review.py"))
    if args.cmd == "commit-checkpoint":
        # Prefer PowerShell twin on Windows; bash script elsewhere.
        if os.name == "nt":
            ps1 = "scripts/commit_checkpoint.ps1"
            if os.path.isfile(ps1):
                return _run([
                    "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", ps1,
                ])
            print(
                "WARN: scripts/commit_checkpoint.ps1 missing; "
                "bash fallback may fail on native Windows."
            )
        return _run(["bash", "scripts/commit_checkpoint.sh"])
    if args.cmd == "agentic":
        if args.agentic_cmd == "tools":
            cmd = _py_cmd("3_bootstrap_scripts/agentic_tools.py", args.tools_cmd)
            if args.tools_cmd in ("enable", "disable"):
                cmd.extend(args.tool_ids)
            elif args.tools_cmd == "profile":
                cmd.append(args.name)
            return _run(cmd)
        cmd = _py_cmd("3_bootstrap_scripts/agentic_session.py", args.agentic_cmd)
        return _run(cmd)

    if args.cmd in ("inspect", "plan", "doctor", "diff", "release", "validate-platform"):
        cmd = _py_cmd(
            "3_bootstrap_scripts/platform_cli.py",
            args.cmd if args.cmd != "validate-platform" else "validate",
        )
        if args.cmd in ("inspect", "plan"):
            if getattr(args, "goal", ""):
                cmd.extend(["--goal", args.goal])
            if getattr(args, "json", False):
                cmd.append("--json")
        return _run(cmd)

    if args.cmd == "child":
        cmd = _py_cmd("3_bootstrap_scripts/platform_cli.py", "child", args.child_cmd)
        if args.child_cmd == "register":
            cmd.append(args.location)
            if getattr(args, "repository_id", ""):
                cmd.extend(["--repository-id", args.repository_id])
            if getattr(args, "name", ""):
                cmd.extend(["--name", args.name])
            if getattr(args, "remote", ""):
                cmd.extend(["--remote", args.remote])
            if getattr(args, "initializer_version", ""):
                cmd.extend(["--initializer-version", args.initializer_version])
        elif args.child_cmd == "status":
            cmd.append(args.repository_id)
        return _run(cmd)

    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
