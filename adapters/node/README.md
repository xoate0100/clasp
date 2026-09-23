# Node / TypeScript reference adapter

Falsifiability adapter for v4: complete the lifecycle **without Python**.

```text
.\meta.ps1 <verb>     # with 0_phase0_bootstrap/stack_adapter.yaml → adapter: node
```

| Verb | Implementation |
|------|----------------|
| init | `scripts/init.mjs` |
| generate-context | `scripts/generate-context.mjs` |
| validate | `scripts/validate.mjs` (+ lefthook.yml) |
| check-updates | `scripts/check-updates.mjs` |
| apply-updates | `scripts/apply-updates.mjs` (dry-run default; `--apply` to copy) |
| submit-feedback | `scripts/submit-feedback.mjs` → `feedback_event` JSON |
| health | `scripts/health.mjs` |

`forbidden_sync_globs` in the manifest prevent Python trees from being pulled onto Node children.
