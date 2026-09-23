# Audit Command Suite

Reusable `/audit-*` commands for the project_initializer hub. Authored here once,
propagated to spokes (CutRates, SureWealth Education, future children) via
`templates/catalog/TEMPLATE_CATALOG.yaml` → catalog id `commands.audit_suite`.

## Layout

- `_skeleton.md` — shared execution contract, finding schema, severity model,
  output layout, agentic rules. Every command inherits it.
- `AUDIT_REGISTRY.yaml` — **source of truth**. Machine-readable manifest agents
  read to discover, stack-gate, and dispatch commands.
- `audit-*.md` — one file per command (the domain prompt body).
- `README.md` — this index.

## How to run

**In Cursor (human):** type `/audit-media` (etc.) in the agent panel.
Add `--fix` to move from read-only discovery into fixing:
`/audit-media --fix --scope app/(marketing)`.

**Agentically (Claude Code / orchestrator / CI):** read `AUDIT_REGISTRY.yaml`,
gate each command by `applies_to` vs this repo's `stack_adapter.yaml`, then for
each: read its `command_file`, follow the `_skeleton.md` phases, and write outputs
to its `output_dir`. `/audit-all` does this for the whole gated subset and merges
the registers.

## Modes

`discovery` is the default and is **non-destructive** — read-only inspection plus
isolated audit utilities under `docs/audit/`. `fix` is opt-in; irreversible or
cross-repo actions route through `NEEDS-ANDY/GATES.yaml` and are never taken
autonomously. Commands never modify initializer-owned meta-framework paths
(`meta.ps1`, `meta.sh`, `agentic/`, numbered spine dirs) — see `CURSOR_RULES.md`.

## Outputs

Each run writes `INVENTORY.md`, `COVERAGE_MATRIX.md`, `FINDINGS.md`, and
`REMEDIATION_PROMPT.md` under `docs/audit/<domain>/`.

## Adding a command

1. Copy an existing `audit-*.md` as a starting shape.
2. Add its entry to `AUDIT_REGISTRY.yaml` (`applies_to`, `output_dir`,
   `depends_on`, `related`).
3. Add its `id` to `audit-all`'s `depends_on`.
4. Keep shared machinery in `_skeleton.md`; only domain checks go in the body.

## Stack gating

`applies_to` values: `next` (Next16/React19/TS/Tailwind4/shadcn/Supabase-SSR/pnpm),
`node`, `python`, `any`. A Python spoke inherits the suite but only runs commands
tagged `python`/`any`, consistent with the v4 contract/adapter split.
