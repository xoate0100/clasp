# Stack Adapter Protocol (index)

Language-neutral meta-framework protocol for v4+.

| Artifact | Role |
|----------|------|
| [`COMMAND_INTERFACE.md`](./COMMAND_INTERFACE.md) | Lifecycle verbs, I/O, exit codes |
| [`HOOK_CONTRACT.md`](./HOOK_CONTRACT.md) | Required checks; runner-agnostic |
| [`TEMPLATE_UPDATE_CONTRACT.md`](./TEMPLATE_UPDATE_CONTRACT.md) | What syncs to which children |
| [`../7_schemas/stack_adapter.schema.json`](../7_schemas/stack_adapter.schema.json) | Adapter manifest schema |
| [`../7_schemas/feedback_event.schema.json`](../7_schemas/feedback_event.schema.json) | Feedback JSON wire format |

Existing declarative specs remain part of the protocol:

- `0_phase0_bootstrap/feature_flags.yml`
- `0_phase0_bootstrap/MVP_SPECIFICATION.yaml`
- `0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml`
- Registries under `5_reference_architectures/`
- Schemas under `7_schemas/`

**Rule:** Python is the *reference adapter*, not the protocol. Node (and future stacks) MUST
satisfy the same verbs without Python.
