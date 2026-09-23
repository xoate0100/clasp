# Template Update Contract

**Status:** protocol (language-neutral)  
**Version:** 1.0.0  
**Related:** `COMMAND_INTERFACE.md` verbs `check-updates` / `apply-updates`,  
`0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml`, `7_schemas/stack_adapter.schema.json`

---

## 1. Goal

Template updates keep children current with the **neutral protocol** and their **selected
stack adapter** — without forcing foreign-stack toolchains onto the child.

---

## 2. Sync classes

| Class | Paths (conceptual) | Who receives |
|-------|-------------------|--------------|
| **Neutral protocol** | `1_global_standards/`, `5_reference_architectures/`, `7_schemas/`, protocol docs under `0_phase0_bootstrap/` that are stack-agnostic, `8_ci/` shared workflows that are adapter-aware | **Every** child |
| **Selected adapter** | `adapters/<id>/` plus adapter-declared extra paths | Only children with `adapter: <id>` |
| **Hub-only / app-layer** | `docs/analysis/`, sample apps, unrelated adapters | **Never** auto-synced to children |
| **Protected** | `MVP_SPECIFICATION.yaml`, `feature_flags.yml`, project dirs (`frontend/`, `backend/`, …), `6_ai_runtime_context/` | Never overwritten by default |

### Transitional rule (v4 migration)

Until Python scripts fully live under `adapters/python/`:

- Children with `adapter: python` MAY continue to sync `3_bootstrap_scripts/`, `agentic/`,
  `agent_platform/` (legacy layout).
- Children with any other adapter MUST NOT receive `3_bootstrap_scripts/**/*.py` as required
  runtime. Prefer `adapters/<id>/` only.

---

## 3. Adapter selection

Children declare active adapter in (first match wins):

1. `0_phase0_bootstrap/stack_adapter.yaml` → `adapter` field  
2. `0_phase0_bootstrap/feature_flags.yml` → `meta_framework.adapter` (optional key)  
3. Default for migrated v3 children: **`python`** (zero behavior change)

---

## 4. `check-updates` behavior

1. Read local `template_version`.
2. Resolve hub `META_FRAMEWORK_VERSION.yaml` (or release API).
3. Report whether remote > local.
4. Warn-only by default (exit `0`); `--strict` may exit `1` when behind.

---

## 5. `apply-updates` behavior

1. Run check-updates; abort if already current (unless `--force`).
2. Fetch hub revision.
3. Copy **neutral protocol** paths.
4. Copy **selected adapter** paths only.
5. Run adapter migration hooks if version jump declares them.
6. Append `update_history` entry.
7. Must not copy other adapters’ implementation trees.

### Forbidden

- Pushing `adapters/python/` into a Node child.
- Requiring `python` / `pre-commit` on PATH for a non-Python adapter’s apply path.
- Silent overwrite of protected files.

---

## 6. Versioning

- Breaking changes to the neutral protocol ⇒ **major** bump (e.g. 3.x → 4.0.0).
- New adapter or additive schema fields ⇒ minor.
- Migrations MUST provide `adapter: python` default with identical behavior for existing children.

---

## 7. Feedback

Failures during check/apply SHOULD emit feedback events:

- `UPDATE_ISSUE` for generic update failures
- `STACK_COUPLING` when an update path requires a foreign runtime
