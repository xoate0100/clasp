# Audit Command Skeleton (shared spine)

> This file is inherited by every `/audit-*` command. Command bodies define
> **domain-specific** scope, inventory targets, and checks; this file defines the
> **shared** execution contract, finding schema, severity model, output layout,
> and agentic invocation rules. Do not duplicate this content in command bodies —
> reference it: "Follow the shared flow in `_skeleton.md`."
>
> `_`-prefixed files are conventions/support, not invocable commands.

---

## 1. Execution contract (every command)

Run the command in five ordered phases:

1. **Scope + rules of engagement** — resolve `applies_to` against this repo's
   `stack_adapter.yaml`/`config.json`. If the stack doesn't match, stop and say so.
   Confirm the run **mode** (below). State the target scope explicitly.
2. **Inventory** — build the domain inventory the command body specifies before
   testing anything. Inventory is evidence, not a formality.
3. **Checks** — run the command body's checks. Prefer live/observed evidence over
   assumption. Pursue edge cases, not just happy paths.
4. **Findings** — record every issue in the finding schema (§4), separating
   **Confirmed** from **Suspected**.
5. **Remediation** — produce the phased plan and emit the output files (§5).

## 2. Modes (non-destructive by default)

- `discovery` (**default**) — read-only. May create isolated, non-destructive
  test scripts, read-only queries, and audit utilities under the output dir. Must
  **not** mutate application code, data, config, or infra.
- `fix` — opt-in only, requested explicitly (`/audit-x --fix` or a follow-up).
  Even in `fix`, irreversible or cross-repo actions route through
  `NEEDS-ANDY/GATES.yaml` and are never taken autonomously.

Invocation args (convention):
`/audit-<domain> [--fix] [--scope <path|route|glob>] [--since <ref>]`

## 3. Severity & priority (shared scale)

Rate every finding on both axes, then map to a priority.

- **Severity** (technical blast radius): `critical | high | medium | low | info`.
- **Likelihood** (how readily it bites): `high | moderate | low`.
- **Priority** (fix order):
  - **P0** — security/privacy/data-integrity risk, or a fully broken critical path.
  - **P1** — broken core workflow, auth/authz gap, or user-blocking defect.
  - **P2** — missing connection, incomplete implementation, state inconsistency.
  - **P3** — polish, hardening, docs, or product-coherence gap.

Security-specific scoring (CVSS + NIST 800-30) lives in `/audit-security-nist`;
other commands use the scale above and hand security-class findings to it.

## 4. Finding schema

Record each finding as a block. Keep IDs stable within a run: `F-001`, `F-002`, …
(prefix per domain if merging registers, e.g. `MEDIA-F-001`).

```
### F-00N — <concise title>
- status:        Confirmed | Suspected
- severity:      critical|high|medium|low|info
- priority:      P0|P1|P2|P3
- affected:      <role / route / file / service / table>
- method:        examine | test | interview  (how it was found)
- repro:         <minimal, replayable steps>
- expected:      <intended behavior>
- actual:        <observed behavior>
- evidence:      <path/line, request/response, screenshot ref — secrets redacted>
- root_cause:    <likely cause>
- impact:        <security / data / UX / architectural consequence>
- fix:           <recommended resolution>
- downstream:    <regressions/edge cases the fix may introduce; related findings>
- regression:    <the automated test that proves the fix and prevents recurrence>
```

Anything not fully validated is **Suspected** — state exactly what additional
access or instrumentation would confirm it.

## 5. Outputs (written under the command's `output_dir`)

Every command writes, at minimum:

- `INVENTORY.md` — the domain inventory from phase 2.
- `COVERAGE_MATRIX.md` — each check area × method used × result, so assessment
  gaps are visible (not just findings).
- `FINDINGS.md` — the finding register (§4), sorted by priority.
- `REMEDIATION_PROMPT.md` — an agentic fix prompt (matches the repo's existing
  house pattern) that a follow-up `--fix` run or Claude Code can execute.

Default `output_dir` is `docs/audit/<domain>/`. Never write outside it in
`discovery` mode.

## 6. Phased remediation (shared shape)

Order fixes by risk and dependency, not discovery order:
`Phase 0 immediate risk → Phase 1 broken core → Phase 2 missing connections →
Phase 3 product coherence → Phase 4 reliability/observability →
Phase 5 regression coverage → Phase 6 architecture/future-risk`.
For each fix, state its likely downstream consequences before recommending it.

## 7. Agentic invocation contract

These commands are dual-use: a human runs `/audit-x` in Cursor, **or** an agent
(Claude Code, the orchestrator, CI) dispatches them. An agent MUST:

1. Read `AUDIT_REGISTRY.yaml` to discover commands, their `applies_to`, `modes`,
   `output_dir`, and `depends_on`.
2. Gate by stack: skip commands whose `applies_to` doesn't match this repo.
3. Read the command body file for the domain checks; execute phases §1–§6.
4. Honor `mode`: default `discovery` (no mutations). Only `--fix` may change
   files, and only within the gate rules.
5. Write outputs to `output_dir`; never touch meta-framework paths
   (`meta.ps1`, `meta.sh`, numbered spine dirs, `agentic/`) — those are
   initializer-owned (see `CURSOR_RULES.md`).
6. `/audit-all` enumerates the registry, runs the gated subset, and merges
   registers into `docs/audit/`.

Frontmatter in each command file (`id`, `applies_to`, `modes`, `output_dir`,
`depends_on`, `description`, `argument-hint`) mirrors the registry and is written
to be compatible with both Cursor commands and (via a future `.claude/commands/`
mirror) Claude Code slash-commands. The registry is the source of truth; command
frontmatter is a convenience mirror.
