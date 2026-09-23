# AI Sandbox Execution Rules (L2.5 Single-Agent)

You are the single authorized agent (Cursor Code). You may execute multi-step plans end-to-end.

## Allowed
- Read `6_ai_runtime_context/ACTIVE_PLAN.yaml` and execute tasks sequentially.
- Write/refactor/delete only in: `frontend/`, `backend/`, `shared/`, `tests/`, `docs/`, `scripts/`, `4_docs_index/`, `3_bootstrap_scripts/` (for meta-framework upgrades only), `6_ai_runtime_context/`, `agentic/`, `proposals/`.
- Run and fix pre-commit failures autonomously.
- Commit autonomously **only** if all pre-commit hooks pass.
- **State Transitions (GOVERNED):** Update `ACTIVE_TASK_POINTER.yaml` ONLY via `auto_advance_state.py` protocol:
  - Task completion gate must pass
  - Completion report must be generated
  - Transition must be logged
  - Pointer increments by exactly +1
- Update `INTENT_DECLARATION.json` before code changes.
- Append to `6_ai_runtime_context/ai_feedback_log.json` when guardrails fail.
- Write completion reports under `6_ai_runtime_context/` (TASK_COMPLETION_REPORTS).

## Required (MANDATORY - BLOCKING)

### TDD (Test-Driven Development) - BLOCKING
- **MANDATORY**: Every code change MUST include corresponding test files in the same commit.
- **BLOCKING**: Commits are **BLOCKED** if code files are modified without tests.
- **Process**: Follow Red → Green → Refactor → Document cycle:
  1. **Red**: Write failing test first
  2. **Green**: Implement minimal code to pass test
  3. **Refactor**: Improve code while keeping tests green
  4. **Document**: Update documentation as needed
- **Test File Patterns**:
  - Python: `*_test.py`, `test_*.py`, files in `tests/` directories
  - TypeScript/JavaScript: `*.test.ts`, `*.test.tsx`, `*.spec.ts`, `*.spec.tsx`, files in `test/` directories
- **Reference**: See `1_global_standards/TEST_STRATEGY_TDD.md` for detailed guidance.

### SOLID Principles - BLOCKING
- **MANDATORY**: All code MUST comply with SOLID design principles.
- **BLOCKING**: Commits are **BLOCKED** on SOLID violations:
  - **SRP (Single Responsibility)**: Functions must be ≤ 50 lines
  - **ISP (Interface Segregation)**: Interfaces/types must be ≤ 10 methods/properties
  - **DIP (Dependency Inversion)**: Depend on abstractions (interfaces), not concrete implementations
- **Enforcement**: Pre-commit `architecture-check` hook validates SOLID compliance.
- **Reference**: See `1_global_standards/SOLID_PRINCIPLES.md` for comprehensive guide.

### Commit Frequency - INCREMENTAL COMMITS REQUIRED
- **MANDATORY**: Commit incrementally to prevent large uncommitted changesets.
- **Commit Triggers**:
  - **After completing each phase** (logical task group) OR **every 3-5 tasks**
  - **When file count threshold exceeded**: If `auto_commit: false` but code changes exceed threshold (default: 10 files), commit via checkpoint
  - **When completing logical unit of work**: Always attempt commit when completing a cohesive feature/module
- **Checkpoint Override**: If `commit_checkpoints.force_commit_on_checkpoint: true` is set, commit checkpoints override `auto_commit: false`
- **Large Changeset Warning**: If >20 files changed since last commit, pre-commit hook will warn (non-blocking)
- **Commit Message Format**: MUST include `plan:<plan_id> component:<component> task:<id>`
- **Reference**: See `docs/COMMIT_STRATEGY.md` for detailed commit frequency best practices

### Other Requirements
- Every commit message MUST include: `plan:<plan_id> component:<component> task:<id>`.
- Keep docs in sync; update `docs/*` and regenerate indexes when code changes.
- Obey `5_reference_architectures/LAYER_RULES.yaml` (no cross-component violations).
- Stay inside current plan's scope; do not add new directories unless listed in plan.

## Forbidden
- Editing any files in: `0_phase0_bootstrap/`, `1_global_standards/`, `7_schemas/`, `.github/`, `8_ci/`, `5_reference_architectures/`, `adapters/`.
- Changing governance, CI/CD, or feature flags.
- Pushing to protected branches (PRs only).
- **Direct edits to `ACTIVE_TASK_POINTER.yaml`** - Must use `auto_advance_state.py` protocol.
- **Skipping tasks** - State advancement must increment by exactly +1.
- **Modifying `state_transition_log.jsonl`** - Append-only audit trail, never rewrite.

## Failure Protocol
- If a hook fails: attempt local corrective changes within current task.
- If failure persists after two attempts: append an entry to `6_ai_runtime_context/ai_feedback_log.json` and stop.
