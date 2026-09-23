---
description: RELEASE RUNBOOK — cut v4.2.0 (runtime-safety + exec_guard) after _ship-runtime-safety, tag, propagate
argument-hint: "(run in project_initializer; follow stop-gates)"
id: _release-runtime-safety
---

# Release runbook — runtime safety → minor template release **v4.2.0**

You are releasing the runtime-safety work (already validated and pushed by
`_ship-runtime-safety.md`) as a **minor** template bump so spokes can
`check-updates` / `apply-updates` to it. Run from the **project_initializer**
repo root.

Irreversible/cross-repo steps are governed by `NEEDS-ANDY/GATES.yaml`. **Stop at
every 🛑 gate and get explicit confirmation.** Do not bump past 4.2.0, do not
delete pre-commit/legacy `.sh` (NA-16), and do not execute NA-13/NA-14
education-platform / course-factory migrations from this runbook.

Prerequisite: `_ship-runtime-safety.md` already landed on hub `main` (exec
guard, harness wiring, `/audit-runtime-safety`, registry, installer,
`CURSOR_RULES` mandate). This runbook only versions, tags, and propagates.

---

## Phase 0 — Preconditions
1. Confirm CWD is project_initializer; `git status` clean on `main` tracking
   `origin` (`xoate0100/project_initializer`). Report remote + HEAD.
2. Confirm `template_version` in `0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml`
   is **4.1.0** (or already 4.2.0 if this runbook was partially applied).
3. Confirm ship artifacts exist: `agentic/exec_guard.py`,
   `.cursor/commands/audit-runtime-safety.md`, harness imports `run_guarded`.
4. Checkout `release/runtime-safety-v4.2.0` from up-to-date `main` (or stay on
   `main` if Andy directed a direct cut).

## Phase 1 — Validate (abort on failure)
1. `node --test .cursor/commands/validate_registry.test.mjs`
2. `node .cursor/commands/validate_registry.mjs`
   Expect **16 commands**, `audit-all` covering `audit-runtime-safety`.
3. Smoke (do not commit the log file — it is gitignored):
   `python -c "import agentic.exec_guard, agentic.harness; print('imports ok')"`
   `python -m agentic.exec_guard --timeout 10 -- python -c "print('ok')"`
4. Optional: `npm --prefix adapters/node run validate`. Full `meta.ps1 validate`
   may still fail on **pre-existing** hub hooks; do not treat those as release
   blockers unless this branch introduced them.

## Phase 2 — Propagation (already done in v4.1.0 — verify, don't duplicate)
Confirm, do not re-add:
- `.cursor/commands/` is in `META_FRAMEWORK_VERSION.yaml` `template_directories`
- `.cursor/commands/` is in `adapters/node/scripts/apply-updates.mjs`
  `allowedPrefixes`
- `agentic/` is in Python `template_directories` (so `exec_guard.py` +
  `harness.py` sync to **Python** spokes)

**Adapter split (document in changelog, do not violate):**
- Python spokes receive `agentic/exec_guard.py` + harness wiring +
  `2_framework_templates/CURSOR_RULES.md` mandate.
- Node spokes receive `/audit-runtime-safety` via `.cursor/commands/` only.
  Do **not** copy `agentic/` onto Node spokes (`forbidden` includes Python
  trees). A Node exec-guard is out of scope for 4.2.0.

No further allowlist edits unless verification shows a gap.

## Phase 3 — Version bump + changelog
1. `META_FRAMEWORK_VERSION.yaml`: `template_version: "4.2.0"`;
   `last_updated_at` today UTC; prepend `update_history`:
   `from_version: "4.1.0"` → `to_version: "4.2.0"`, `migration_applied: false`,
   notes covering `/audit-runtime-safety`, `agentic/exec_guard.py`, harness
   wiring, CURSOR_RULES mandate.
2. Optionally set `features.runtime_exec_guard: true`.
3. `adapters/node/package.json` `version` → `4.2.0-dev`.
4. `templates/catalog/TEMPLATE_CATALOG.yaml` `commands.audit_suite` version
   `0.1.0` → `0.2.0`.
5. Prepend `## [4.2.0] - <today>` to `CHANGELOG.md` (`### Added`). Do not
   backfill skipped versions.

## Phase 4 — Commit + push hub
1. Stage only version/changelog/runbook/catalog/node package files (plus any
   Phase 2 gap-fills). Do not stage `6_ai_runtime_context/EXEC_GUARD_LOG.jsonl`.
2. Commit:
   `plan:audit-suite component:runtime-safety task:release-v4.2.0 — version 4.2.0 for exec_guard + /audit-runtime-safety`
3. 🛑 **GATE — show diff + commit, then** `git push -u origin <branch>`.
4. Open PR to `main` if not already on `main`. After CI green, merge (no
   `--no-verify`; do not delete the release branch unless asked).

## Phase 5 — Tag (spokes discover via tags)
`check-updates` uses newest hub **git tag** (`v?[\d.]+`). Untagged commits are
invisible to Node `check-updates`.
1. Fast-forward local `main` to the merge commit.
2. `git tag -a v4.2.0 -m "Runtime safety: exec_guard + /audit-runtime-safety (minor)"`
3. 🛑 **GATE — confirm, then** `git push origin v4.2.0` and
   `gh release create v4.2.0 --title "v4.2.0 — runtime safety" --notes-from changelog`.

## Phase 6 — Propagate to spokes
1. Read `5_reference_architectures/CHILD_REPOSITORY_REGISTRY.yaml` and
   `docs/SPOKE_CANDIDACY_INVENTORY.yaml` `already_spokes`. List targets.
2. **Skip / do not execute:** NA-13 education-platform Node-adapter *migration*;
   NA-14 course-factory *init*; unregistered inventory candidates; `test-child`;
   archived; external forks.
3. 🛑 **GATE — present the spoke list and confirm which to update.**
4. For each **confirmed** spoke:
   a. `check-updates` — expect newest tag `4.2.0`.
   b. Python: `apply-updates` / `update-template` (dry-run then apply).
      Node: `apply-updates --apply` **twice** if allowlists changed (not required
      for 4.2.0 command-only delta; still twice if the spoke is pre-4.1.0).
   c. Verify `.cursor/commands/audit-runtime-safety.md` exists; Python spokes
      also have `agentic/exec_guard.py`. Run
      `node .cursor/commands/validate_registry.mjs`.
   d. Commit `plan:audit-suite component:runtime-safety task:adopt-v4.2.0`.
   e. 🛑 **GATE — confirm before `git push` in the spoke.**

## Phase 7 — Report
Hub version + tag URL; per-spoke updated / skipped / blocked (cite NA-xx);
validator results. Do not claim spokes updated unless the command file (and
Python exec_guard where applicable) is present and the registry validator passed.
