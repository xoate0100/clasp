# Hook Contract

**Status:** protocol (language-neutral)  
**Version:** 1.0.0  
**Satisfiers:** Python `pre-commit`, lefthook, husky, or any runner that executes the required checks.

This contract defines **what** must be enforced — not **which** runner or language implements it.
Stack adapters declare `hook_runner` + per-check commands in the adapter manifest.

---

## 1. Principles

1. Checks are identified by stable **check ids** (below).
2. A runner configuration is conforming iff it invokes a command for every **required** check id
   at the specified stage (`pre-commit`, `pre-push`, or `ci`).
3. Implementing language is irrelevant; exit code `0` = pass, non-zero = fail (unless warn-only).
4. Warn-only checks MUST NOT block; they SHOULD print `[warn]` and exit `0`.

---

## 2. Required checks

| Check id | Stage | Blocking | Intent |
|----------|-------|----------|--------|
| `syntax` | pre-commit | yes | Parse/structural validity of touched sources |
| `format` | pre-commit | yes | Style consistency |
| `static-analysis` | pre-commit | yes | Types / lint for touched stacks |
| `security` | pre-commit | yes | Secrets + high-severity security patterns |
| `architecture` | pre-commit | yes | Layer / SOLID / import boundary rules |
| `guardrails` | pre-commit | yes | Task scope, intent, AI sandbox rules |
| `gates` | pre-commit | yes | Coverage / schema / security gate flags |
| `tests` | pre-commit | yes | Test suite for affected components |
| `docs-sync` | pre-commit | yes | Docs index / required doc updates |
| `template-update-check` | pre-commit | no (warn) | Notify when hub template is newer |
| `context-staleness` | pre-commit | no (warn) | AI context older than sources |

## 3. Recommended checks (adapters SHOULD)

| Check id | Stage | Blocking | Intent |
|----------|-------|----------|--------|
| `resurrection-scan` | pre-commit | yes | Forbidden decision resurrection keywords |
| `governance-drift` | pre-commit | yes | Sandbox vs flags drift |
| `reference-validate` | pre-commit | yes | Broken internal references |
| `commit-message` | commit-msg | yes | Plan/task tags when required |
| `large-changeset` | pre-commit | no (warn) | Oversized diff warning |
| `performance` | pre-commit | no (warn) | Perf regression heuristics |
| `complexity` | pre-commit | no (warn) | Complexity / duplication |

---

## 4. Runner profiles

**Neutral preferred runner (DEC-0004-HOOK-RUNNER / NA-07):** `lefthook`
(cross-platform binary; no Python required to execute hooks).

| Runner | Typical adapter | Notes |
|--------|-----------------|-------|
| `lefthook` | **neutral default** / `node` | Preferred contract satisfier |
| `pre-commit` | `python` | Allowed for the Python reference adapter |
| `husky` + npm scripts | `node` (optional) | Node-only; not the neutral default |
| CI-only | `generic` (v4.1+) | Deferred from v4.0 |

No lifecycle verb may require `bash.exe` (NA-09). Windows entry is `meta.ps1`.

---

## 5. Portability guard

Any **new** check added to the **neutral** protocol MUST:

1. Be expressible as a shell-invocable command (no implicit Python import).
2. Ship an implementation under **every** reference adapter, OR be marked `adapter_optional: true`
   with rationale.
3. Prefer emitting `STACK_COUPLING` feedback if a change re-introduces a single-stack-only
   operational step into the neutral protocol.

---

## 6. Legacy mapping (Python pre-commit ids → contract ids)

| Legacy hook id | Contract check id |
|----------------|-------------------|
| syntax-checks | `syntax` |
| format-style | `format` |
| static-analysis | `static-analysis` |
| security-scan | `security` |
| architecture-check | `architecture` |
| guardrail-enforcement | `guardrails` |
| gate-enforcement | `gates` |
| tests-and-coverage | `tests` |
| documentation-sync | `docs-sync` |
| check-template-updates | `template-update-check` |
| check-context-staleness | `context-staleness` |
| resurrection-scan | `resurrection-scan` |
| governance-drift-validate | `governance-drift` |
| reference-validate | `reference-validate` |
| commit-message-validator | `commit-message` |
| large-changeset-warning | `large-changeset` |
| performance-scan | `performance` |
| complexity-duplication | `complexity` |
