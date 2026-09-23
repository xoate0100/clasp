#!/usr/bin/env python3
"""Run project tests and coverage once per pre-commit invocation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from pre_commit_utils import PIP_TIMEOUT, TEST_TIMEOUT, run_subprocess  # noqa: E402

try:
    import yaml
except ImportError:
    yaml = None


def load_thresholds() -> dict:
    defaults = {
        "backend_threshold": 100,
        "frontend_threshold": 95,
        "block_on_coverage": True,
    }
    flags_path = Path("0_phase0_bootstrap/feature_flags.yml")
    if not flags_path.exists() or yaml is None:
        return defaults
    try:
        with open(flags_path, "r", encoding="utf-8") as handle:
            flags = yaml.safe_load(handle) or {}
        components = flags.get("components", {})
        gates = flags.get("gates", {})
        return {
            "backend_threshold": components.get("backend", {}).get("coverage_threshold", 100),
            "frontend_threshold": components.get("frontend", {}).get("coverage_threshold", 95),
            "block_on_coverage": gates.get("block_on_coverage_drop", True),
        }
    except Exception:
        return defaults


def main() -> int:
    thresholds = load_thresholds()
    status = 0

    if Path("backend").is_dir():
        coverage_file = Path("coverage-backend.dat").resolve()
        env = os.environ.copy()
        env["COVERAGE_FILE"] = str(coverage_file)

        pip = run_subprocess(
            [sys.executable, "-m", "pip", "install", "--quiet", "pytest", "pytest-cov"],
            timeout=PIP_TIMEOUT,
        )
        if pip.returncode != 0:
            return pip.returncode

        pytest = run_subprocess(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--cov=backend",
                "--cov-report=term-missing",
                "--cov-report=json:coverage-backend.json",
            ],
            timeout=TEST_TIMEOUT,
            env=env,
        )
        if pytest.returncode != 0:
            status = 1
        else:
            report = Path("coverage-backend.json")
            if report.exists():
                covered = json.loads(report.read_text(encoding="utf-8"))["totals"]["percent_covered"]
                if covered < thresholds["backend_threshold"] and thresholds["block_on_coverage"]:
                    print(
                        f"[coverage] Backend coverage {covered}% below threshold "
                        f"{thresholds['backend_threshold']}%"
                    )
                    status = 1

    if Path("frontend/package.json").is_file():
        npm_ci = run_subprocess(["npm", "ci", "--silent"], cwd="frontend", timeout=PIP_TIMEOUT)
        if npm_ci.returncode != 0:
            status = 1
        else:
            npm_test = run_subprocess(
                ["npm", "test", "--silent", "--", "--coverage"],
                cwd="frontend",
                timeout=TEST_TIMEOUT,
            )
            if npm_test.returncode != 0:
                status = 1
            else:
                print(
                    f"[coverage] Frontend tests passed (threshold: "
                    f"{thresholds['frontend_threshold']}%)"
                )

    if status != 0:
        print("[tests-coverage] FAILED")
        return 1

    print("[tests-coverage] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
