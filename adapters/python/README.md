# Python reference adapter

This profile is the **backward-compatible** implementation of the v4 stack-agnostic
protocol. Existing children keep working unchanged.

| Artifact | Role |
|----------|------|
| `stack_adapter.yaml` / `.json` | Manifest conforming to `7_schemas/stack_adapter.schema.json` |
| `../../../3_bootstrap_scripts/` | Operational scripts (legacy location; still the runtime) |
| `../../../meta.ps1` / `meta.sh` | Neutral dispatcher entry points |

## Guarantee

A repository with `0_phase0_bootstrap/stack_adapter.yaml` → `adapter: python` behaves
as the pre-v4 Python toolchain: same scripts, same hooks (`pre-commit`), same
`cli.py` surface (plus neutral verb aliases `check-updates` / `apply-updates`).

## Entry points

```text
.\meta.ps1 <verb>          # preferred (Windows)
./meta.sh <verb>           # preferred (POSIX)
python 3_bootstrap_scripts/cli.py <verb>   # legacy; still supported
```

Scripts are not physically relocated in Phase 2 so diffs stay reviewable and
imports keep working. The adapter **owns** the verb→command mapping; future
phases may move files under `adapters/python/lib/` behind the same manifest.
