# Generic / unknown-stack adapter

Fallback adapter for repos that have not yet registered a known `governance_runtime`
(`python`, `node`, …). Selected automatically when
`0_phase0_bootstrap/stack_adapter.yaml` is missing.

## Behavior

| Concern | Behavior |
|---------|----------|
| Selection | `meta` defaults to `generic` when no selection file exists |
| Required verbs | Run `stub_verb.py`; exit **3** naming the missing tool if PATH lacks it |
| `crosswalk` | `python 3_bootstrap_scripts/crosswalk.py` — writes selection + version stub; idempotent |
| `product_stack` | Always informational (`unknown` here); never drives dispatch (DEC-0005) |

## Usage

```bash
# Greenfield / unknown stack
./meta.ps1 crosswalk
./meta.sh crosswalk
```

After onboard, replace selection with a real adapter when known:

```yaml
# 0_phase0_bootstrap/stack_adapter.yaml
adapter: python
manifest: adapters/python/stack_adapter.yaml
```

## Must not

- Infer product language from `governance_runtime`
- Require inventing a PHP (or other product) adapter merely because `product_stack` names that language
