#!/usr/bin/env python3
"""
Dynamic AI Context Generator

Generates a consolidated AI execution context document from meta-framework source files.
This document serves as the primary constraint context for AI chat sessions.

Purpose:
- Consolidate constraints from multiple files into single document
- Include current state, flags, task context
- Auto-regenerate on state/flag changes
- Minimize human interaction (automated workflows)

Usage:
    python 3_bootstrap_scripts/generate_ai_context.py

Output:
    6_ai_runtime_context/AI_CONTEXT.md
"""

import sys
import pathlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install PyYAML")
    sys.exit(1)


def read_file(path: pathlib.Path, description: str) -> Optional[str]:
    """Read file content with error handling"""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        print(f"WARN: {description} not found: {path}")
        return None
    except Exception as e:
        print(f"WARN: Error reading {description}: {e}")
        return None


def extract_sandbox_rules(content: str) -> Dict[str, List[str]]:
    """Extract rules from AI_SANDBOX_RULES.md"""
    rules = {
        "allowed": [],
        "required": [],
        "forbidden": []
    }

    if not content:
        return rules

    lines = content.splitlines()
    current_section = None

    for line in lines:
        line_lower = line.lower()

        # Detect section headers
        if "## Allowed" in line:
            current_section = "allowed"
            continue
        elif "## Required" in line or "## MANDATORY" in line:
            current_section = "required"
            continue
        elif "## Forbidden" in line:
            current_section = "forbidden"
            continue
        elif line.startswith("##"):
            current_section = None
            continue

        # Extract list items
        if current_section and line.strip().startswith("-"):
            rule_text = line.strip()[1:].strip()
            if rule_text:
                rules[current_section].append(rule_text)

    return rules


def parse_feature_flags(content: str) -> Dict[str, Dict[str, bool]]:
    """Parse feature flags from feature_flags.yml"""
    flags = {
        "enabled": {},
        "disabled": {}
    }

    if not content:
        return flags

    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            return flags

        # Extract mode flags
        mode = data.get("mode", {})
        if isinstance(mode, dict):
            for key, value in mode.items():
                if isinstance(value, bool):
                    if value:
                        flags["enabled"][key] = True
                    else:
                        flags["disabled"][key] = True

        # Extract ai_guardrails
        guardrails = data.get("ai_guardrails", {})
        if isinstance(guardrails, dict):
            for key, value in guardrails.items():
                if isinstance(value, bool):
                    if value:
                        flags["enabled"][f"guardrail_{key}"] = True
                    else:
                        flags["disabled"][f"guardrail_{key}"] = True

        # Extract permissions
        permissions = data.get("permissions", {})
        if isinstance(permissions, dict):
            write_to = permissions.get("write_to", [])
            if isinstance(write_to, list):
                flags["enabled"]["write_paths"] = write_to

    except Exception as e:
        print(f"WARN: Error parsing feature flags: {e}")

    return flags


def parse_active_plan(content: str) -> Dict[str, any]:
    """Parse active plan from ACTIVE_PLAN.yaml"""
    plan = {
        "plan_id": "",
        "component": "",
        "goal": "",
        "current_task": None,
        "status": "",
        "tasks": []
    }

    if not content:
        return plan

    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            return plan

        plan["plan_id"] = data.get("plan_id", "")
        plan["component"] = data.get("component", "")
        plan["goal"] = data.get("goal", "")
        plan["status"] = data.get("status", "")
        plan["tasks"] = data.get("tasks", [])

    except Exception as e:
        print(f"WARN: Error parsing active plan: {e}")

    return plan


def parse_task_pointer(content: str) -> Dict[str, any]:
    """Parse task pointer from ACTIVE_TASK_POINTER.yaml"""
    pointer = {
        "current_task": None,
        "status": "",
        "last_run": None
    }

    if not content:
        return pointer

    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            return pointer

        pointer["current_task"] = data.get("current_task")
        pointer["status"] = data.get("status", "")
        pointer["last_run"] = data.get("last_run")

    except Exception as e:
        print(f"WARN: Error parsing task pointer: {e}")

    return pointer


def discover_enforcement_tools(scripts_dir: pathlib.Path) -> List[Dict[str, str]]:
    """Discover enforcement tools from 3_bootstrap_scripts/"""
    tools = []

    if not scripts_dir.exists():
        return tools

    for script_file in scripts_dir.glob("*.py"):
        if script_file.name == "generate_ai_context.py":
            continue  # Skip self

        # Read first 10 lines to extract description
        try:
            content = script_file.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()[:10]

            description = ""
            for line in lines:
                # Look for docstring or comment description
                if line.strip().startswith('"""') or line.strip().startswith("'''"):
                    # Extract from docstring
                    desc_start = line.find('"""') + 3
                    if desc_start > 3:
                        description = line[desc_start:].strip()
                        break
                elif line.strip().startswith("#") and "description" in line.lower():
                    # Extract from comment
                    description = line.strip()[1:].strip()
                    break

            if not description:
                description = f"Enforcement tool: {script_file.name}"

            tools.append({
                "name": script_file.name,
                "description": description
            })
        except Exception as e:
            print(f"WARN: Error reading tool {script_file.name}: {e}")

    return sorted(tools, key=lambda x: x["name"])


def parse_decision_registry(content: str) -> Dict[str, any]:
    """Parse decision registry for active decisions and forbidden keywords."""
    result = {
        "decisions": [],
        "forbidden_keywords": [],
        "open_decisions": [],
    }

    if not content:
        return result

    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            return result

        for row in data.get("decisions") or []:
            if not isinstance(row, dict):
                continue
            decision_id = row.get("decision_id", "")
            status = row.get("status", "")
            result["decisions"].append(row)
            if status == "proposed":
                result["open_decisions"].append(decision_id)
            if status in ("accepted", "proposed"):
                for keyword in row.get("resurrection_trigger_keywords") or []:
                    if not str(keyword).startswith("REPLACE_"):
                        result["forbidden_keywords"].append(keyword)
    except Exception as e:
        print(f"WARN: Error parsing decision registry: {e}")

    return result


def parse_agent_registry(content: str) -> Dict[str, any]:
    """Parse agent registry for role summary."""
    result = {"agents": []}
    if not content:
        return result
    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            return result
        for agent in data.get("agents") or []:
            if isinstance(agent, dict) and agent.get("id"):
                result["agents"].append(agent)
    except Exception as e:
        print(f"WARN: Error parsing agent registry: {e}")
    return result


def parse_drift_vectors(content: str) -> List[Dict[str, str]]:
    """Parse drift vector catalog."""
    vectors: List[Dict[str, str]] = []
    if not content:
        return vectors
    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            return vectors
        for vector in data.get("vectors") or []:
            if isinstance(vector, dict) and vector.get("id"):
                vectors.append(vector)
    except Exception as e:
        print(f"WARN: Error parsing drift vectors: {e}")
    return vectors


def parse_layer_rules(content: str) -> Dict[str, any]:
    """Parse layer rules from LAYER_RULES.yaml"""
    rules = {
        "components": {},
        "layers": [],
        "rules": {}
    }

    if not content:
        return rules

    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            return rules

        rules["components"] = data.get("components", {})
        rules["layers"] = data.get("layers", [])
        rules["rules"] = data.get("rules", {})

    except Exception as e:
        print(f"WARN: Error parsing layer rules: {e}")

    return rules


def generate_context_document(
    sandbox_rules: Dict[str, List[str]],
    feature_flags: Dict[str, Dict[str, bool]],
    active_plan: Dict[str, any],
    task_pointer: Dict[str, any],
    enforcement_tools: List[Dict[str, str]],
    layer_rules: Dict[str, any],
    decision_registry: Dict[str, any],
    agent_registry: Dict[str, any],
    drift_vectors: List[Dict[str, str]],
) -> str:
    """Generate the AI context document"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Find current task
    current_task_id = task_pointer.get("current_task")
    current_task = None
    if current_task_id and active_plan.get("tasks"):
        for task in active_plan["tasks"]:
            if isinstance(task, dict) and task.get("id") == current_task_id:
                current_task = task
                break

    # Build document
    doc = []
    doc.append("# AI Execution Context - Auto-Generated\n")
    doc.append(f"**Generated:** {timestamp}\n")
    doc.append("**Authority:** `0_phase0_bootstrap/AI_SANDBOX_RULES.md`\n")
    doc.append("**Purpose:** Consolidated constraint context for AI chat sessions\n")
    doc.append("\n---\n")

    # Governance Section (MUST be at top, after header)
    doc.append("## Governance\n")
    doc.append("**Source:** `1_global_standards/AI_OPERATING_CONSTITUTION.md`\n")
    doc.append("\n**Core Non-Negotiable Rules:**\n")
    doc.append("- Authority must be explicit or it does not exist\n")
    doc.append("- State must be read, never inferred\n")
    doc.append("- Generated artifacts are derivative\n")
    doc.append("- No action without explicit permission\n")
    doc.append("- If unsure, stop\n")
    doc.append("- AI may not modify governance\n")
    doc.append("\n**Reference:** See `1_global_standards/AI_OPERATING_CONSTITUTION.md` for complete governance rules.\n")
    doc.append("\n---\n")

    # Current State Context
    doc.append("## Current State Context\n")
    if active_plan.get("plan_id"):
        doc.append(f"**Plan:** {active_plan['plan_id']}\n")
    if active_plan.get("component"):
        doc.append(f"**Component:** {active_plan['component']}\n")
    if current_task:
        doc.append(f"**Current Task:** {current_task.get('id')} - {current_task.get('name', 'N/A')}\n")
    elif current_task_id:
        doc.append(f"**Current Task:** {current_task_id}\n")
    doc.append(f"**Status:** {active_plan.get('status', 'unknown')}\n")

    if active_plan.get("tasks"):
        next_task = None
        for task in active_plan["tasks"]:
            if isinstance(task, dict) and task.get("id") == current_task_id:
                # Find next task
                idx = active_plan["tasks"].index(task)
                if idx + 1 < len(active_plan["tasks"]):
                    next_task = active_plan["tasks"][idx + 1]
                break
        if next_task:
            doc.append(f"**Next Task:** {next_task.get('id')} - {next_task.get('name', 'N/A')}\n")

    doc.append("\n**Blocking Issues:** None\n")  # TODO: Extract from feedback log if needed
    doc.append("\n---\n")

    # Agentic Coordination
    doc.append("## Agentic Coordination\n")
    doc.append("**Source:** `5_reference_architectures/DECISION_REGISTRY.yaml`\n\n")

    if decision_registry.get("open_decisions"):
        doc.append("### Open decisions (require explicit resolution)\n")
        for decision_id in decision_registry["open_decisions"]:
            doc.append(f"- **{decision_id}**: status `proposed` — do not implement conflicting work\n")
        doc.append("\n")

    if decision_registry.get("forbidden_keywords"):
        doc.append("### Forbidden resurrection keywords (pre-commit + CI enforced)\n")
        for keyword in decision_registry["forbidden_keywords"][:20]:
            doc.append(f"- `{keyword}`\n")
        if len(decision_registry["forbidden_keywords"]) > 20:
            doc.append(f"- ... and {len(decision_registry['forbidden_keywords']) - 20} more\n")
        doc.append("\n")

    if drift_vectors:
        doc.append("### Named drift vectors\n")
        doc.append("**Reference:** `5_reference_architectures/DRIFT_VECTORS.yaml`\n\n")
        for vector in drift_vectors[:10]:
            doc.append(f"- **{vector.get('id', 'N/A')}**: {vector.get('description', '')}\n")
        doc.append("\n")

    if agent_registry.get("agents"):
        doc.append("### Agent role graph\n")
        for agent in agent_registry["agents"]:
            tools = ", ".join(agent.get("tools") or [])
            doc.append(f"- **{agent.get('id')}**: {agent.get('role', '')} — tools: [{tools}]\n")
        doc.append("\n**Reference:** `5_reference_architectures/AGENT_REGISTRY.yaml`\n\n")
        doc.append("**Session commands:**\n")
        doc.append("- Session start: `python 3_bootstrap_scripts/agentic_session.py session-start`\n")
        doc.append("- Pre-commit review: `python 3_bootstrap_scripts/agentic_session.py pre-commit-review`\n")
        doc.append("- Graph playbook: `python 3_bootstrap_scripts/agentic_session.py graph playbook`\n")
        doc.append("\n")

    doc.append("### Optional in-project tools\n")
    doc.append("**Catalog:** `5_reference_architectures/OPTIONAL_AGENTIC_TOOLS.yaml`\n\n")
    doc.append("Toggle via `python 3_bootstrap_scripts/cli.py agentic tools list|enable|disable|profile`.\n\n")
    doc.append("| Tool | Purpose |\n|------|--------|\n")
    doc.append("| knowledge_index | Local BM25 RAG from KNOWLEDGE_SOURCES.yaml |\n")
    doc.append("| doc_lifecycle | PROJECT_STATUS.md, archive/deprecate workflow |\n")
    doc.append("| janitor | Session-start staleness refresh |\n")
    doc.append("| governance_drift_validator | feature_flags vs AI_SANDBOX_RULES alignment |\n")
    doc.append("| reference_validator | Unresolved imports and path literals |\n")
    doc.append("\n")

    doc.append("\n---\n")

    # Sandbox Rules
    doc.append("## Sandbox Rules\n")

    if sandbox_rules.get("allowed"):
        doc.append("### Allowed\n")
        for rule in sandbox_rules["allowed"]:
            doc.append(f"- {rule}\n")
        doc.append("\n")

    if sandbox_rules.get("required"):
        doc.append("### Required (MANDATORY - BLOCKING)\n")
        for rule in sandbox_rules["required"]:
            doc.append(f"- {rule}\n")
        doc.append("\n")

    if sandbox_rules.get("forbidden"):
        doc.append("### Forbidden\n")
        for rule in sandbox_rules["forbidden"]:
            doc.append(f"- {rule}\n")
        doc.append("\n")

    doc.append("**Reference:** `0_phase0_bootstrap/AI_SANDBOX_RULES.md`\n")
    doc.append("\n---\n")

    # Feature Flags
    doc.append("## Feature Flags\n")

    if feature_flags.get("enabled"):
        doc.append("### Enabled Permissions\n")
        for flag_name, _ in sorted(feature_flags["enabled"].items()):
            doc.append(f"- **{flag_name}**: Enabled\n")
        doc.append("\n")

    if feature_flags.get("disabled"):
        doc.append("### Disabled Permissions\n")
        for flag_name, _ in sorted(feature_flags["disabled"].items()):
            doc.append(f"- **{flag_name}**: Disabled\n")
        doc.append("\n")

    doc.append("**Reference:** `0_phase0_bootstrap/feature_flags.yml`\n")
    doc.append("\n---\n")

    # Current Task Context
    doc.append("## Current Task Context\n")
    if current_task:
        doc.append(f"**Task {current_task.get('id')}:** {current_task.get('name', 'N/A')}\n")
        outputs = current_task.get("outputs", [])
        if outputs:
            doc.append("**Outputs:**\n")
            for output in outputs:
                doc.append(f"- {output}\n")
    else:
        doc.append("**No active task**\n")

    doc.append(f"\n**Full Plan:** See `6_ai_runtime_context/ACTIVE_PLAN.yaml`\n")
    doc.append("\n---\n")

    # Enforcement Tools
    if enforcement_tools:
        doc.append("## Enforcement Tools Available\n")
        for tool in enforcement_tools:
            doc.append(f"- **{tool['name']}**: {tool['description']}\n")
        doc.append("\n**Location:** `3_bootstrap_scripts/`\n")
        doc.append("\n---\n")

    # Architecture Rules
    if layer_rules.get("components") or layer_rules.get("layers"):
        doc.append("## Architecture Rules\n")

        if layer_rules.get("components"):
            doc.append("### Component Boundaries\n")
            for comp_name, comp_config in layer_rules["components"].items():
                doc.append(f"- **{comp_name}**:\n")
                if isinstance(comp_config, dict):
                    may_import = comp_config.get("may_import", [])
                    forbid_import = comp_config.get("forbid_import", [])
                    if may_import:
                        doc.append(f"  - May import: {', '.join(may_import)}\n")
                    if forbid_import:
                        doc.append(f"  - Forbidden imports: {', '.join(forbid_import)}\n")
            doc.append("\n")

        if layer_rules.get("layers"):
            doc.append("### Layer Rules\n")
            for layer in layer_rules["layers"]:
                if isinstance(layer, dict):
                    doc.append(f"- **{layer.get('name', 'N/A')}**: {layer.get('may_import', [])}\n")
            doc.append("\n")

        doc.append("**Reference:** `5_reference_architectures/LAYER_RULES.yaml`\n")
        doc.append("\n---\n")

    # Reference Documents
    doc.append("## Reference Documents\n")
    doc.append("For complete details, see:\n\n")
    doc.append("1. **`1_global_standards/AI_OPERATING_CONSTITUTION.md`** - Governance and operating rules (MANDATORY)\n")
    doc.append("2. **`0_phase0_bootstrap/AI_SANDBOX_RULES.md`** - Sandbox execution rules\n")
    doc.append("3. **`0_phase0_bootstrap/feature_flags.yml`** - Feature flags and permissions\n")
    doc.append("4. **`6_ai_runtime_context/ACTIVE_PLAN.yaml`** - Current plan and tasks\n")
    doc.append("5. **`6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml`** - Current task pointer\n")
    doc.append("6. **`5_reference_architectures/LAYER_RULES.yaml`** - Architecture boundaries\n")
    doc.append("7. **`5_reference_architectures/DECISION_REGISTRY.yaml`** - Machine-checkable ADRs\n")
    doc.append("8. **`5_reference_architectures/AGENT_REGISTRY.yaml`** - Agent role graph and tools\n")
    doc.append("9. **`1_global_standards/`** - Code standards (TDD, SOLID, etc.)\n")
    doc.append("\n---\n")

    # Auto-Advance Protocol
    doc.append("## Auto-Advance Protocol\n")
    doc.append("**State transitions are governed by the Auto-Advance Protocol:**\n\n")
    doc.append("1. **Task Completion Gate** must pass (all 6 gates validated)\n")
    doc.append("2. **Completion Report** generated at `6_ai_runtime_context/TASK_COMPLETION_REPORTS/task_<id>.md`\n")
    doc.append("3. **State Transition** logged to `6_ai_runtime_context/state_transition_log.jsonl`\n")
    doc.append("4. **Pointer Updated** via `auto_advance_state.py` (increments by exactly +1)\n\n")
    doc.append("**To advance state:**\n")
    doc.append("```bash\n")
    doc.append("python3 3_bootstrap_scripts/auto_advance_state.py\n")
    doc.append("```\n\n")
    doc.append("**DO NOT edit ACTIVE_TASK_POINTER.yaml directly.**\n")
    doc.append("State transitions require gate validation and audit logging.\n")
    doc.append("\n---\n")

    # Usage Instructions
    doc.append("## Usage Instructions\n")
    doc.append("**For AI Agents:**\n")
    doc.append("1. Load this document first in new chat sessions\n")
    doc.append("2. Reference authoritative documents for complete details\n")
    doc.append("3. Use enforcement tools listed above for validation\n")
    doc.append("4. Regenerate if state/flags change during session\n")
    doc.append("5. Use `auto_advance_state.py` to advance task state (never edit pointer directly)\n")
    doc.append("\n")
    doc.append("**For Human Operators:**\n")
    doc.append("- Auto-regenerates on state/flag changes\n")
    doc.append("- Pre-commit hook warns if stale\n")
    doc.append("- Manual: `python 3_bootstrap_scripts/generate_ai_context.py`\n")
    doc.append("\n---\n")
    doc.append(f"\n**Last Generated:** {timestamp}\n")
    doc.append("**Generator:** `3_bootstrap_scripts/generate_ai_context.py`\n")

    try:
        from agentic.context_fingerprint import compute_context_fingerprint

        fingerprint = compute_context_fingerprint(pathlib.Path(".").resolve())
        doc.append(f"**Content fingerprint:** `{fingerprint}`\n")
    except Exception:
        pass

    return "".join(doc)


def main() -> int:
    """Main generation function"""
    root = pathlib.Path(".").resolve()

    # Source file paths
    constitution_path = root / "1_global_standards" / "AI_OPERATING_CONSTITUTION.md"
    sandbox_rules_path = root / "0_phase0_bootstrap" / "AI_SANDBOX_RULES.md"
    feature_flags_path = root / "0_phase0_bootstrap" / "feature_flags.yml"
    active_plan_path = root / "6_ai_runtime_context" / "ACTIVE_PLAN.yaml"
    task_pointer_path = root / "6_ai_runtime_context" / "ACTIVE_TASK_POINTER.yaml"
    layer_rules_path = root / "5_reference_architectures" / "LAYER_RULES.yaml"
    decision_registry_path = root / "5_reference_architectures" / "DECISION_REGISTRY.yaml"
    agent_registry_path = root / "5_reference_architectures" / "AGENT_REGISTRY.yaml"
    drift_vectors_path = root / "5_reference_architectures" / "DRIFT_VECTORS.yaml"
    scripts_dir = root / "3_bootstrap_scripts"
    
    # Verify constitution file exists (required for governance)
    if not constitution_path.exists():
        print("ERROR: AI_OPERATING_CONSTITUTION.md not found at 1_global_standards/AI_OPERATING_CONSTITUTION.md")
        print("This file is required for governance installation.")
        return 1

    # Output path
    output_path = root / "6_ai_runtime_context" / "AI_CONTEXT.md"

    # Read source files
    sandbox_rules_content = read_file(sandbox_rules_path, "AI_SANDBOX_RULES.md")
    feature_flags_content = read_file(feature_flags_path, "feature_flags.yml")
    active_plan_content = read_file(active_plan_path, "ACTIVE_PLAN.yaml")
    task_pointer_content = read_file(task_pointer_path, "ACTIVE_TASK_POINTER.yaml")
    layer_rules_content = read_file(layer_rules_path, "LAYER_RULES.yaml")
    decision_registry_content = read_file(decision_registry_path, "DECISION_REGISTRY.yaml")
    agent_registry_content = read_file(agent_registry_path, "AGENT_REGISTRY.yaml")
    drift_vectors_content = read_file(drift_vectors_path, "DRIFT_VECTORS.yaml")

    # Extract/parse data
    sandbox_rules = extract_sandbox_rules(sandbox_rules_content)
    feature_flags = parse_feature_flags(feature_flags_content)
    active_plan = parse_active_plan(active_plan_content)
    task_pointer = parse_task_pointer(task_pointer_content)
    enforcement_tools = discover_enforcement_tools(scripts_dir)
    layer_rules = parse_layer_rules(layer_rules_content)
    decision_registry = parse_decision_registry(decision_registry_content)
    agent_registry = parse_agent_registry(agent_registry_content)
    drift_vectors = parse_drift_vectors(drift_vectors_content)

    # Generate document
    document = generate_context_document(
        sandbox_rules,
        feature_flags,
        active_plan,
        task_pointer,
        enforcement_tools,
        layer_rules,
        decision_registry,
        agent_registry,
        drift_vectors,
    )

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")

    print(f"[generate-context] OK: Generated {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
