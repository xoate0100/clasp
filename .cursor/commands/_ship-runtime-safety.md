---
description: RUNBOOK — validate, test, and commit/push the audit-suite + runtime-safety work from project_initializer
argument-hint: "(run in project_initializer; stop at the push gate)"
id: _ship-runtime-safety
---

# Ship runbook — validate, test, commit/push (audit suite + runtime safety)

Run this from the **project_initializer** repo root. It validates the command
suite, tests the new runtime-safety code, and commits/pushes the pending work to
the hub. The final push is irreversible — **stop at the 🛑 gate and get explicit
confirmation.** This runbook does NOT bump the version, tag, or propagate to
spokes; that's `_release-audit-suite.md` (run it after this to cut v4.1.0).

Only the specific edits below are intended; do not touch other meta-framework
logic.

## Phase 0 — Preconditions
1. Confirm CWD is the project_initializer repo; run `git status` and report the
   pending changes. Expect (uncommitted): `agentic/exec_guard.py`,
   `agentic/harness.py`, `.cursor/commands/` (suite + `audit-runtime-safety.md` +
   `AUDIT_REGISTRY.yaml` + `audit-all.md` + validator/tests + runbooks),
   `.cursor/install-global.ps1`, `templates/catalog/TEMPLATE_CATALOG.yaml`,
   `2_framework_templates/CURSOR_RULES.md`.
2. Confirm `git remote -v` `origin` is the hub (`xoate0100/project_initializer`)
   and report the current branch.
3. Ensure the exec-guard log won't be committed: if
   `6_ai_runtime_context/EXEC_GUARD_LOG.jsonl` is not already git-ignored, add that
   path to `.gitignore` (the test steps below will generate it).

## Phase 1 — Validate the command suite (abort on any failure)
1. `node --test .cursor/commands/validate_registry.test.mjs` — validator unit
   tests (valid suite passes; missing file / id mismatch / orphan / missing
   support file all caught). Must exit 0.
2. `node .cursor/commands/validate_registry.mjs` — live registry check. Expect
   **16 commands**, `audit-all` covering all of them, no orphans, frontmatter ids
   matching. Must exit 0. If it fails, fix and re-run before continuing.

## Phase 2 — Test the runtime-safety code
Run from repo root so `import agentic...` resolves.
1. **Import sanity** (proves the harness edits + guard import load):
   `python -c "import agentic.exec_guard, agentic.harness; print('imports ok')"`
2. **psutil presence** (memory/cpu/fork-bomb caps need it):
   `python -c "import psutil; print('psutil', psutil.__version__)"` — if this
   fails, note that those three caps are best-effort; timeout + output cap still
   hold. (Optionally add `psutil` to `adapters/python` requirements.)
3. **Guard functional smoke tests** — prove it actually kills. These run
   intentionally naughty commands *under the guard*, which is the point:
   - Clean run: `python -m agentic.exec_guard --timeout 10 -- python -c "print('ok')"`
     → expect `rc=0`, not killed.
   - Timeout/infinite-loop: `python -m agentic.exec_guard --timeout 3 -- python -c "while True: pass"`
     → expect KILLED, reason `wall-timeout`, ~3s, non-zero rc.
   - Output flood: `python -m agentic.exec_guard --max-output-bytes 200000 -- python -c "import sys\nwhile True: sys.stdout.write('x'*10000)"`
     → expect KILLED, reason `output-flood`.
   - (psutil only) subprocess/fork guard is exercised by anything spawning many
     children; skip if psutil absent.
4. **Log check**: confirm `6_ai_runtime_context/EXEC_GUARD_LOG.jsonl` now has one
   JSON line per run above, each with `killed`/`reason`/`duration_s`.
5. **Harness regression** (guarded `script` path still works end-to-end): run an
   existing pipeline, e.g.
   `python -c "from agentic.harness import run_validator_pipeline; import sys; sys.exit(run_validator_pipeline())"`
   — should behave as before (now buffered, printed at end). Report exit code.
6. **Repo validation / lint** so pre-commit will pass: run what the repo exposes —
   `./meta.ps1 validate` (Windows) / `./meta.sh validate` (POSIX), or
   `npm --prefix adapters/node run validate`, plus Python lint (ruff) and any
   `pytest`. Fix until green.

## Phase 3 — Commit (hub)
1. Stage the pending files from Phase 0 (including this runbook and the new
   `.cursor/commands/audit-runtime-safety.md`), but NOT
   `6_ai_runtime_context/EXEC_GUARD_LOG.jsonl` (git-ignored in Phase 0).
2. Commit with the house format (`CURSOR_RULES.md`):
   `plan:audit-suite component:runtime-safety task:add-exec-guard — /audit-runtime-safety + agentic/exec_guard.py guarded runner wired through harness; CURSOR_RULES exec-safety mandate; registry+installer updated`
   Prefer `commit-checkpoint` if available
   (`python3 3_bootstrap_scripts/cli.py commit-checkpoint`) so hooks run.
3. If >10–20 files stage at once, that's expected here (first landing of the
   suite + runtime safety) — commit anyway per the commit-frequency rules.

## Phase 4 — Push
🛑 **GATE — show the diff summary and the exact commit, then confirm before push.**
On confirmation: `git push origin <branch>`.

## Phase 5 — Report + handoff
Summarize: validator result (command count), each guard smoke-test outcome
(killed/clean + reason), harness regression exit code, lint/validation status, and
the commit hash pushed. Then note the next step: run `_release-audit-suite.md` to
cut **v4.1.0**, tag, and propagate to spokes (this runbook intentionally stopped at
the hub). Do not claim the release is done — only that the work is validated,
tested, and pushed to the hub branch.
