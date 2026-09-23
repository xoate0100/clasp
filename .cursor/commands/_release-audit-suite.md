---
description: RELEASE RUNBOOK — validate the audit-suite, cut a minor template release (v4.1.0), propagate to spokes
argument-hint: "(run in project_initializer; follow stop-gates)"
id: _release-audit-suite
---

# Release runbook — audit command suite → minor template release

You are releasing the `/audit-*` command suite as a **minor** version bump of the
project_initializer template and propagating it to spokes. Run this from the
**project_initializer** repo root. This runbook performs irreversible, cross-repo
actions (git push, spoke commits) — **stop at every 🛑 gate and get explicit
human confirmation before proceeding**. Irreversible/cross-repo steps are governed
by `NEEDS-ANDY/GATES.yaml`; do not bypass it.

Do not edit meta-framework logic beyond the two specific propagation-allowlist
changes named in Phase 2 — those are the intended release changes.

---

## Phase 0 — Preconditions
1. Confirm CWD is the project_initializer repo and `git status` is clean (or only
   the intended audit-suite files are staged/untracked). Report the working tree.
2. Confirm `git remote -v` `origin` points at the hub
   (`xoate0100/project_initializer`). Report it.
3. Confirm the current branch. If releases are cut from `main`, be on `main`;
   otherwise create/checkout a `release/audit-suite-v4.1.0` branch and note it.
4. Read `0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml` and report the current
   `template_version` (expected `4.0.0`).

## Phase 1 — Validate (abort on any failure)
1. Run the suite validator (unit tests + live check):
   `node --test .cursor/commands/validate_registry.test.mjs`  (validator logic)
   `node .cursor/commands/validate_registry.mjs`               (real registry)
   Both must exit 0 (every command_file exists, frontmatter ids match, no orphans,
   audit-all covers all commands). If either fails, fix and re-run — **do not
   release a failing suite.**
2. Run the repo's own validation so pre-commit will pass. Use whichever the repo
   exposes (check before assuming): the neutral dispatcher `./meta.ps1 validate`
   (Windows) / `./meta.sh validate` (POSIX), or the Node adapter
   `npm --prefix adapters/node run validate`. Report results; fix lint/format
   issues until green.

## Phase 2 — Close the propagation gaps (required, or spokes won't receive the suite)
The suite lives in `.cursor/commands/`, which is currently **not** a propagated
path. Make exactly these two edits:

1. **Python update path** — in
   `0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml`, add `.cursor/commands/` to
   the `template_directories:` list.
2. **Node update path** — in `adapters/node/scripts/apply-updates.mjs`, add
   `.cursor/commands/` to the `allowedPrefixes` array.
3. **Verify the Python adapter** actually syncs from `template_directories` (grep
   `adapters/python/` and `3_bootstrap_scripts/` for the update/copy logic). If it
   uses a separate hardcoded allowlist, add `.cursor/commands/` there too. If it
   reads `template_directories`, step 1 already covers it — say so.
4. Re-run `node .cursor/commands/validate_registry.mjs` (should still pass).

## Phase 3 — Version bump + changelog
1. In `META_FRAMEWORK_VERSION.yaml`: set `template_version: "4.1.0"`; update
   `last_updated_at` to today (UTC); append an `update_history` entry:
   `from_version: "4.0.0" → to_version: "4.1.0"`, `migration_applied: false`,
   notes: "Audit command suite: /audit-* Cursor commands + AUDIT_REGISTRY manifest
   + registry validator; .cursor/commands/ added to propagation allowlists."
2. Optionally bump `adapters/node/package.json` `version` `4.0.0-dev` → `4.1.0-dev`.
3. Prepend a `## [4.1.0] - <today>` section to `CHANGELOG.md` (Keep a Changelog
   format, `### Added`) summarizing the suite. Note: the changelog is behind the
   version history — do **not** backfill 2.1→4.0; only add the 4.1.0 entry.

## Phase 4 — Commit (upstream / hub)
1. Stage the audit-suite files, the two allowlist edits, the version file, and the
   changelog.
2. Commit using the house message format (see `CURSOR_RULES.md`):
   `plan:audit-suite component:commands task:release-v4.1.0 — add /audit-* suite + registry validator; wire .cursor/commands propagation`
   Prefer `commit-checkpoint` if available
   (`python3 3_bootstrap_scripts/cli.py commit-checkpoint`) so hooks run; otherwise
   a normal commit after Phase 1 validation passed.
3. 🛑 **GATE — show the diff summary and the exact commit, then confirm before push.**
   On confirmation: `git push origin <branch>`.

## Phase 5 — Tag the release (spokes detect updates by tag)
`check-updates` compares a spoke's local `template_version` to the newest **git
tag** on the hub (`git ls-remote --tags`, pattern `v?[\d.]+`). So the release is
only visible to spokes once tagged.
1. Create an annotated tag: `git tag -a v4.1.0 -m "Audit command suite (minor)"`.
2. 🛑 **GATE — confirm, then** `git push origin v4.1.0`.

## Phase 6 — Propagate to spokes
1. Enumerate spokes from the child registry (read
   `5_reference_architectures/` — e.g. `CHILD_REGISTRY.yaml` / child registry) and
   list them. Node-adapter spokes (e.g. surewealth-education-platform, the course
   factory) are the targets; skip any Python-only spoke that can't run the Node
   validator unless its Python update path was covered in Phase 2.
2. 🛑 **GATE — present the spoke list and confirm which to update.**
3. For **each confirmed spoke**, in that spoke's working copy:
   a. `check-updates` via its dispatcher — expect `update_available=true`
      (newest_tag `4.1.0` ≠ local).
   b. **Run `apply-updates --apply` TWICE (important):** the spoke's *current*
      adapter still has the old allowlist, so pass 1 syncs `adapters/node/`
      (installing the new allowlist that now includes `.cursor/commands/`); pass 2
      then actually copies `.cursor/commands/` into the spoke. (Alternatively, seed
      `.cursor/commands/` once by hand, then a single apply-updates keeps it in
      sync going forward.) Confirm `.cursor/commands/` now exists in the spoke.
   c. Bump the spoke's `template_version` to `4.1.0` (apply-updates/migration may do
      this; verify) and run `node .cursor/commands/validate_registry.mjs` in the
      spoke — must pass.
   d. Run the spoke's own validation so its hooks pass.
   e. Commit in the spoke with the house format
      (`plan:audit-suite component:commands task:adopt-v4.1.0`).
   f. 🛑 **GATE — confirm before `git push` in the spoke.**

## Phase 7 — Report
Summarize: hub version + tag pushed; per-spoke adoption status (updated / skipped /
failed) and validator results; anything that needs follow-up (e.g. a Python spoke
not yet covered, or a spoke where two-pass apply-updates didn't seed the commands).
Do **not** claim spokes are updated unless `.cursor/commands/` is present and the
validator passed in each.
