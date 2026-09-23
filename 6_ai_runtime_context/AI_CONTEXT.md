# AI Execution Context - Auto-Generated
**Generated:** 2026-09-22 22:37:45
**Authority:** `0_phase0_bootstrap/AI_SANDBOX_RULES.md`
**Purpose:** Consolidated constraint context for AI chat sessions

---
## Governance
**Source:** `1_global_standards/AI_OPERATING_CONSTITUTION.md`

**Core Non-Negotiable Rules:**
- Authority must be explicit or it does not exist
- State must be read, never inferred
- Generated artifacts are derivative
- No action without explicit permission
- If unsure, stop
- AI may not modify governance

**Reference:** See `1_global_standards/AI_OPERATING_CONSTITUTION.md` for complete governance rules.

---
## Current State Context
**Plan:** clasp-child-init
**Component:** backend
**Current Task:** 1 - Confirm node adapter and inherited template version
**Status:** active
**Next Task:** 2 - Preserve clasp source, tests, and existing CI

**Blocking Issues:** None

---
## Agentic Coordination
**Source:** `5_reference_architectures/DECISION_REGISTRY.yaml`

### Forbidden resurrection keywords (pre-commit + CI enforced)
- `split into separate repos`
- `polyrepo`
- `separate frontend repo`
- `separate backend repo`
- `require python for node children`
- `ship all bootstrap scripts to every stack`
- `delete python adapter`
- `pre-commit only forever`
- `require husky for all stacks`
- `infer stack from adapter`
- `php adapter required`
- `governance runtime equals product stack`
- `require php adapter for CutRatesLMS`
- `channel-specific publish contract`
- `wordpress publish fork`
- `lms publish contract separate`
- `live publish without human gate`
- `separate publish digest per channel`
- `auto live publish agent`

### Named drift vectors
**Reference:** `5_reference_architectures/DRIFT_VECTORS.yaml`

- **DV_HOOK_BYPASS**: Skipping pre-commit hooks or guardrails to force commits through
- **DV_GOVERNANCE_DIRECT_EDIT**: Direct edits to locked governance files outside the decision registry process
- **DV_PREMATURE_ORCHESTRATION**: Standing up Kubernetes/orchestration before a real multi-service scaling need exists
- **DV_DB_FROM_API**: Direct DB calls from api/ or domain/ layers, bypassing infra/
- **DV_SPLIT_WITHOUT_CRITERIA**: Repo split proposed without documented split criteria
- **DV_CI_GUARDRAIL_BYPASS**: CI runs pre-commit with || true or omits blocking guardrail steps

### Agent role graph
- **spec_reader**: Load active MVP phase, open decisions, and current task context — tools: [load_mvp_phase, load_decision_registry, read_layer_rules, knowledge_query]
- **implementer**: Write code/tests within allowed paths only; never touches locked governance files — tools: [read_layer_rules, read_decision_registry]
- **validator**: Run layer/architecture checks, tests, schema validation — tools: [architecture_check, layer_rules_check, run_tests, schema_validate]
- **reviewer**: Drift-vector + resurrection scan; checks scope against phase gate — tools: [resurrection_scan, drift_vector_check, phase_gate_check]
- **decision_proposer**: ONLY role allowed to draft a DECISION_REGISTRY.yaml row; requires human approval to merge — tools: [decision_registry_validate]

**Reference:** `5_reference_architectures/AGENT_REGISTRY.yaml`

**Session commands:**
- Session start: `python 3_bootstrap_scripts/agentic_session.py session-start`
- Pre-commit review: `python 3_bootstrap_scripts/agentic_session.py pre-commit-review`
- Graph playbook: `python 3_bootstrap_scripts/agentic_session.py graph playbook`

### Optional in-project tools
**Catalog:** `5_reference_architectures/OPTIONAL_AGENTIC_TOOLS.yaml`

Toggle via `python 3_bootstrap_scripts/cli.py agentic tools list|enable|disable|profile`.

| Tool | Purpose |
|------|--------|
| knowledge_index | Local BM25 RAG from KNOWLEDGE_SOURCES.yaml |
| doc_lifecycle | PROJECT_STATUS.md, archive/deprecate workflow |
| janitor | Session-start staleness refresh |
| governance_drift_validator | feature_flags vs AI_SANDBOX_RULES alignment |
| reference_validator | Unresolved imports and path literals |


---
## Sandbox Rules
### Allowed
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

### Forbidden
- Editing any files in: `0_phase0_bootstrap/`, `1_global_standards/`, `7_schemas/`, `.github/`, `8_ci/`, `5_reference_architectures/`, `adapters/`.
- Changing governance, CI/CD, or feature flags.
- Pushing to protected branches (PRs only).
- **Direct edits to `ACTIVE_TASK_POINTER.yaml`** - Must use `auto_advance_state.py` protocol.
- **Skipping tasks** - State advancement must increment by exactly +1.
- **Modifying `state_transition_log.jsonl`** - Append-only audit trail, never rewrite.

**Reference:** `0_phase0_bootstrap/AI_SANDBOX_RULES.md`

---
## Feature Flags
### Enabled Permissions
- **agentic_write_ops**: Enabled
- **guardrail_allow_context_files_in_any_commit**: Enabled
- **guardrail_enforce_agentic_coordination**: Enabled
- **guardrail_enforce_intent_declaration**: Enabled
- **guardrail_enforce_solid_principles**: Enabled
- **guardrail_enforce_task_scope**: Enabled
- **guardrail_enforce_tdd_cycle**: Enabled
- **guardrail_forbid_folder_creation_outside_scope**: Enabled
- **guardrail_require_commit_plan_tags**: Enabled
- **guardrail_require_doc_sync**: Enabled
- **human_review_required_for_merge**: Enabled
- **write_paths**: Enabled

### Disabled Permissions
- **modify_meta_framework**: Disabled

**Reference:** `0_phase0_bootstrap/feature_flags.yml`

---
## Current Task Context
**Task 1:** Confirm node adapter and inherited template version
**Outputs:**
- 0_phase0_bootstrap/stack_adapter.yaml
- 0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml

**Full Plan:** See `6_ai_runtime_context/ACTIVE_PLAN.yaml`

---
## Enforcement Tools Available
- **agent_registry_validate.py**: Enforcement tool: agent_registry_validate.py
- **agentic_coordinate_validate.py**: Enforcement tool: agentic_coordinate_validate.py
- **agentic_janitor.py**: Enforcement tool: agentic_janitor.py
- **agentic_session.py**: Enforcement tool: agentic_session.py
- **agentic_tools.py**: Enforcement tool: agentic_tools.py
- **ai_behavior_validation.py**: Enforcement tool: ai_behavior_validation.py
- **ai_reasoning_tuner.py**: Enforcement tool: ai_reasoning_tuner.py
- **ai_review.py**: Enforcement tool: ai_review.py
- **anti_bypass_scan.py**: Enforcement tool: anti_bypass_scan.py
- **append_state_transition.py**: Enforcement tool: append_state_transition.py
- **apply_proposed_fix.py**: Enforcement tool: apply_proposed_fix.py
- **architecture_check.py**: Enforcement tool: architecture_check.py
- **audit_and_update_docs.py**: Enforcement tool: audit_and_update_docs.py
- **auto_advance_state.py**: Enforcement tool: auto_advance_state.py
- **backlog_clear_gate.py**: Enforcement tool: backlog_clear_gate.py
- **check_context_staleness.py**: Enforcement tool: check_context_staleness.py
- **check_governance_install.py**: Enforcement tool: check_governance_install.py
- **check_large_changeset.py**: Enforcement tool: check_large_changeset.py
- **check_state_transition.py**: Enforcement tool: check_state_transition.py
- **check_template_updates.py**: Enforcement tool: check_template_updates.py
- **cli.py**: Enforcement tool: cli.py
- **commit_validator.py**: Enforcement tool: commit_validator.py
- **complexity_check.py**: Enforcement tool: complexity_check.py
- **crosswalk.py**: Enforcement tool: crosswalk.py
- **decision_registry_validate.py**: Enforcement tool: decision_registry_validate.py
- **detect_environment.py**: Enforcement tool: detect_environment.py
- **docs_archive.py**: Enforcement tool: docs_archive.py
- **docs_sync.py**: Enforcement tool: docs_sync.py
- **drift_analyzer.py**: Enforcement tool: drift_analyzer.py
- **drift_vector_check.py**: Enforcement tool: drift_vector_check.py
- **drift_vectors_validate.py**: Enforcement tool: drift_vectors_validate.py
- **emit_workspace_feedback.py**: Enforcement tool: emit_workspace_feedback.py
- **enforce_format.py**: Enforcement tool: enforce_format.py
- **factory_run.py**: Enforcement tool: factory_run.py
- **feedback_collector.py**: Enforcement tool: feedback_collector.py
- **feedback_logger.py**: Enforcement tool: feedback_logger.py
- **fleet_backlog_status.py**: Enforcement tool: fleet_backlog_status.py
- **fleet_ratchet.py**: Enforcement tool: fleet_ratchet.py
- **fleet_upgrade.py**: Enforcement tool: fleet_upgrade.py
- **gate_enforcement.py**: Enforcement tool: gate_enforcement.py
- **gates_check.py**: Enforcement tool: gates_check.py
- **generate_hook_config.py**: Enforcement tool: generate_hook_config.py
- **governance_drift_validate.py**: Enforcement tool: governance_drift_validate.py
- **governance_gap_status.py**: Enforcement tool: governance_gap_status.py
- **governance_scope.py**: Enforcement tool: governance_scope.py
- **guardrail_enforcement.py**: Enforcement tool: guardrail_enforcement.py
- **init_project.py**: Enforcement tool: init_project.py
- **init_versioning.py**: Enforcement tool: init_versioning.py
- **init_wizard.py**: Enforcement tool: init_wizard.py
- **install_hooks.py**: Enforcement tool: install_hooks.py
- **knowledge_index_build.py**: Enforcement tool: knowledge_index_build.py
- **knowledge_query.py**: Enforcement tool: knowledge_query.py
- **knowledge_sources_validate.py**: Enforcement tool: knowledge_sources_validate.py
- **layout_adaptor.py**: Enforcement tool: layout_adaptor.py
- **match_issue.py**: Enforcement tool: match_issue.py
- **migrate_v0_to_initializer.py**: Enforcement tool: migrate_v0_to_initializer.py
- **module_registry_validate.py**: Enforcement tool: module_registry_validate.py
- **performance_scan.py**: Enforcement tool: performance_scan.py
- **phase_gate.py**: Enforcement tool: phase_gate.py
- **platform_cli.py**: Enforcement tool: platform_cli.py
- **platform_validate.py**: Enforcement tool: platform_validate.py
- **plumbing_fleet_scan.py**: Enforcement tool: plumbing_fleet_scan.py
- **portability_guard.py**: Enforcement tool: portability_guard.py
- **pre_commit_utils.py**: Enforcement tool: pre_commit_utils.py
- **query_issue_knowledge.py**: Enforcement tool: query_issue_knowledge.py
- **readiness_check.py**: Enforcement tool: readiness_check.py
- **reference_validate.py**: Enforcement tool: reference_validate.py
- **resurrection_scan.py**: Enforcement tool: resurrection_scan.py
- **run_behavioral_miner.py**: Enforcement tool: run_behavioral_miner.py
- **run_remediation_agent.py**: Enforcement tool: run_remediation_agent.py
- **schema_enforcement.py**: Enforcement tool: schema_enforcement.py
- **security_scan.py**: Enforcement tool: security_scan.py
- **standardized_feedback.py**: Enforcement tool: standardized_feedback.py
- **static_analysis.py**: Enforcement tool: static_analysis.py
- **sync_standards.py**: Enforcement tool: sync_standards.py
- **task_completion_gate.py**: Enforcement tool: task_completion_gate.py
- **task_workflow_helper.py**: Enforcement tool: task_workflow_helper.py
- **template_update.py**: Enforcement tool: template_update.py
- **test_task1_gate.py**: Enforcement tool: test_task1_gate.py
- **tests_coverage.py**: Enforcement tool: tests_coverage.py
- **traceability_graph.py**: Enforcement tool: traceability_graph.py
- **upgrade_legacy_project.py**: Enforcement tool: upgrade_legacy_project.py
- **validate_syntax.py**: Enforcement tool: validate_syntax.py
- **vercel_deployment_tracker.py**: Enforcement tool: vercel_deployment_tracker.py
- **workspace_feedback_sink.py**: Enforcement tool: workspace_feedback_sink.py
- **workspace_spine_validate.py**: Enforcement tool: workspace_spine_validate.py

**Location:** `3_bootstrap_scripts/`

---
## Architecture Rules
### Component Boundaries
- **frontend**:
  - May import: shared
  - Forbidden imports: backend
- **backend**:
  - May import: shared
  - Forbidden imports: frontend
- **shared**:
  - Forbidden imports: frontend, backend

### Layer Rules
- **api**: ['domain']
- **domain**: ['infra']
- **infra**: []

**Reference:** `5_reference_architectures/LAYER_RULES.yaml`

---
## Reference Documents
For complete details, see:

1. **`1_global_standards/AI_OPERATING_CONSTITUTION.md`** - Governance and operating rules (MANDATORY)
2. **`0_phase0_bootstrap/AI_SANDBOX_RULES.md`** - Sandbox execution rules
3. **`0_phase0_bootstrap/feature_flags.yml`** - Feature flags and permissions
4. **`6_ai_runtime_context/ACTIVE_PLAN.yaml`** - Current plan and tasks
5. **`6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml`** - Current task pointer
6. **`5_reference_architectures/LAYER_RULES.yaml`** - Architecture boundaries
7. **`5_reference_architectures/DECISION_REGISTRY.yaml`** - Machine-checkable ADRs
8. **`5_reference_architectures/AGENT_REGISTRY.yaml`** - Agent role graph and tools
9. **`1_global_standards/`** - Code standards (TDD, SOLID, etc.)

---
## Auto-Advance Protocol
**State transitions are governed by the Auto-Advance Protocol:**

1. **Task Completion Gate** must pass (all 6 gates validated)
2. **Completion Report** generated at `6_ai_runtime_context/TASK_COMPLETION_REPORTS/task_<id>.md`
3. **State Transition** logged to `6_ai_runtime_context/state_transition_log.jsonl`
4. **Pointer Updated** via `auto_advance_state.py` (increments by exactly +1)

**To advance state:**
```bash
python3 3_bootstrap_scripts/auto_advance_state.py
```

**DO NOT edit ACTIVE_TASK_POINTER.yaml directly.**
State transitions require gate validation and audit logging.

---
## Usage Instructions
**For AI Agents:**
1. Load this document first in new chat sessions
2. Reference authoritative documents for complete details
3. Use enforcement tools listed above for validation
4. Regenerate if state/flags change during session
5. Use `auto_advance_state.py` to advance task state (never edit pointer directly)

**For Human Operators:**
- Auto-regenerates on state/flag changes
- Pre-commit hook warns if stale
- Manual: `python 3_bootstrap_scripts/generate_ai_context.py`

---

**Last Generated:** 2026-09-22 22:37:45
**Generator:** `3_bootstrap_scripts/generate_ai_context.py`
