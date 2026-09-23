---
description: Orchestrator — enumerate the registry, run the stack-gated subset, merge findings registers
argument-hint: "[--fix] [--only <ids>] [--skip <ids>]"
id: audit-all
applies_to: [any]
modes: [discovery, fix]
output_dir: docs/audit/
depends_on: [audit-security-nist, audit-completeness, audit-uiux, audit-media, audit-optimization, audit-journey, audit-conversion, audit-seo, audit-integrations, audit-data, audit-infra, audit-dependencies, audit-observability, audit-docs, audit-runtime-safety]
related: []
---

# /audit-all — orchestrator

Follow the shared flow in `_skeleton.md`. Runs the whole suite for this repo.

## Procedure
1. Read `.cursor/commands/AUDIT_REGISTRY.yaml`.
2. Resolve this repo's stack from `stack_adapter.yaml`/`config.json`.
3. Select commands whose `applies_to` matches the stack (minus `--skip`, or only
   `--only` if given). Respect `depends_on` ordering.
4. Run each selected command per its body, honoring the run `mode`
   (`discovery` default; `--fix` propagates to children under the gate rules).
5. Write each command's outputs to its own `output_dir`.

## Merge
After the subset runs, produce in `docs/audit/`:
- `INDEX.md` — which commands ran, which were skipped (and why: stack gate), and
  links to each domain's outputs.
- `FINDINGS.md` — merged register across domains, de-duplicated (one finding per
  root issue even if surfaced by several commands), sorted by priority.
- `COVERAGE_MATRIX.md` — aggregate: domain × ran? × key areas covered.
- `EXECUTIVE_SUMMARY.md` — release-readiness verdict in plain language, with the
  P0/P1 count as the gate.
- `REMEDIATION_PROMPT.md` — merged, phased fix prompt for a follow-up `--fix` run.

## Gate
Do not report "release-ready" while any P0/P1 is open or any critical workflow or
authorization boundary is untested. Defer to `/audit-security-nist`'s gate for the
security verdict.
