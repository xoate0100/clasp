#!/usr/bin/env python3
"""
Gate enforcement module.
Implements gate checks from feature_flags.yml (warn_on_performance_regression, warn_on_mutation_drop)
"""
import sys
import pathlib

try:
    import yaml
except ImportError:
    print("[gate] ERROR: PyYAML required for gate enforcement")
    print("[gate] Install with: pip install PyYAML")
    sys.exit(1)


def load_feature_flags():
    """Load feature flags configuration"""
    flags_path = pathlib.Path("0_phase0_bootstrap/feature_flags.yml")
    if not flags_path.exists():
        return {}
    return yaml.safe_load(open(flags_path))


def warn_on_performance_regression(gates: dict, thresholds: dict):
    """
    Gate: warn_on_performance_regression
    Integrate with CI perf benchmark; log warnings only.
    """
    if not gates.get("warn_on_performance_regression", False):
        return True  # Not enabled

    threshold = thresholds.get("perf_regression_pct", 10)

    # Stub: Placeholder for performance testing
    # TODO: Integrate with actual performance benchmarking
    perf_report = pathlib.Path("ai_reports/performance_report.json")

    if not perf_report.exists():
        print("[gate] warn_on_performance_regression: No performance report found")
        print("  Tip: Run performance benchmarks to enable regression detection")
        return True  # Warning only

    # TODO: Parse performance report and check for regressions
    # For now, just log that the gate is active
    print(f"[gate] warn_on_performance_regression: Active (threshold: {threshold}%)")
    print("  Status: Performance regression detection not yet implemented")
    print("  Action: This is a stub - implement performance benchmarking")

    return True


def warn_on_mutation_drop(gates: dict, thresholds: dict):
    """
    Gate: warn_on_mutation_drop
    Stub mutation-testing job; mark TODO until engine implemented.
    """
    if not gates.get("warn_on_mutation_drop", False):
        return True  # Not enabled

    threshold = thresholds.get("mutation_kill", 75)

    # Stub: Placeholder for mutation testing
    mutation_report = pathlib.Path("ai_reports/mutation_report.json")

    if not mutation_report.exists():
        print("[gate] warn_on_mutation_drop: No mutation test report found")
        print("  Tip: Run mutation tests to enable mutation score tracking")
        return True  # Warning only

    # TODO: Parse mutation report and check for drops
    print(f"[gate] warn_on_mutation_drop: Active (threshold: {threshold}%)")
    print("  Status: Mutation testing not yet implemented")
    print("  Action: This is a stub - implement mutation testing (e.g., mutmut, stryker)")

    return True


def main():
    """Main gate enforcement"""
    flags = load_feature_flags()
    gates = flags.get("gates", {})
    thresholds = flags.get("thresholds", {})

    if not gates:
        print("[gate] No gates configured")
        sys.exit(0)

    results = []

    # Run gate checks (warnings only, non-blocking)
    results.append(warn_on_performance_regression(gates, thresholds))
    results.append(warn_on_mutation_drop(gates, thresholds))

    # Gates are warnings, so always exit 0
    print("[gate] Gate checks complete (warnings only)")
    sys.exit(0)


if __name__ == "__main__":
    main()
